-- dbt/models/intermediate/int_delinquency_path.sql
{{ config(materialized='ephemeral') }}

-- Per loan x month-on-book delinquency BUCKET, via a deterministic synthetic state machine.
--
-- HONESTY: LendingClub is a loan-level snapshot with only a TERMINAL status and no monthly
-- DPD history. This model GENERATES the intermediate 30/60/90 path, but pins each loan's
-- terminal absorbing state (charged_off / paid) and its approximate charge-off month to the
-- REAL observed outcome. Only the walk between "current" and the absorbing state is synthetic.
-- Read roll rates built on this as an illustrative transition structure, not servicing data.
--
-- Ephemeral on purpose: the per-loan-month grain is large; only the small mart_roll_rates
-- aggregate is persisted (the project's $0 / free-tier rule, same as fct_loan_month).

with loan as (

    select
        loan_id,
        issue_date,
        term_months,
        default_flag,
        fully_paid_flag,
        is_right_censored,
        observed_mob,
        -- charge-off MOB, approximated as fct_loan_month does, then CAPPED at
        -- observed_mob: the approximation is +/-1-3 months, and capping guarantees every
        -- charged-off loan's path really absorbs to 'charged_off' inside its observed
        -- window (terminal state = real outcome, the model's core promise).
        case
            when default_flag = 1
            then least(
                greatest(1, date_diff(charge_off_date_approx, issue_date, month)),
                observed_mob
            )
        end as charge_off_mob
    from {{ ref('fct_loan') }}

),

spine as (

    select
        loan.*,
        mob
    from loan,
        -- only OBSERVED months: never fabricate a path beyond the snapshot. A loan with
        -- observed_mob < 1 (issued at/after the snapshot month) yields an EMPTY array ->
        -- zero rows, not a fabricated month.
        unnest(generate_array(1, loan.observed_mob)) as mob

),

bucketed as (

    select
        loan_id,
        issue_date,
        mob,
        observed_mob,
        charge_off_mob,
        case
            -- charged-off loans: current until the 3-month run-up, then 30->60->90->CO
            when default_flag = 1 and charge_off_mob is not null then
                case
                    when mob >= charge_off_mob                 then 'charged_off'
                    when mob = charge_off_mob - 1              then 'dpd_90_plus'
                    when mob = charge_off_mob - 2              then 'dpd_60'
                    when mob = charge_off_mob - 3              then 'dpd_30'
                    else 'current'
                end
            -- fully-paid loans: current throughout, absorb to 'paid' at the last observed mob
            when fully_paid_flag = 1 then
                if(mob >= least(observed_mob, term_months), 'paid', 'current')
            -- still-active (right-censored) loans: current for every observed month
            else 'current'
        end as bucket
    from spine

)

select
    loan_id,
    concat(cast(extract(year from issue_date) as string), '-Q',
           cast(extract(quarter from issue_date) as string)) as issue_year_quarter,
    mob,
    bucket,
    lead(bucket) over (partition by loan_id order by mob) as next_bucket
from bucketed
