{{ config(materialized='view') }}

-- Fact: one row per loan x month-on-book (MOB). GENERATED via a date-spine
-- cross join (each loan against MOB 1..term), because LendingClub is a loan-level
-- SNAPSHOT with no monthly payment history.
--
-- Materialized as a VIEW on purpose: at ~97M rows a table would break the project's
-- $0 free-tier storage goal (BQ 10 GB is shared across projects). The C1.5 marts
-- aggregate this into small cohort x MOB tables; nothing large is persisted.
--
-- Honesty caveats (documented, not hidden):
--   * charge-off MONTH is approximated from last_pymnt_date -> +/- 1-3 months noise.
--   * MOBs beyond the 2019-03 snapshot are right-censored: is_observed = false.

with loan as (

    select
        loan_id,
        issue_date,
        term_months,
        loan_amnt,
        default_flag,
        observed_mob,
        -- realized principal loss for charged-off loans (non-negative)
        greatest(0, funded_amnt - total_rec_prncp - recoveries) as net_chargeoff_amount,
        -- charge-off MOB approximated from the (approximate) charge-off month
        case
            when default_flag = 1
            then greatest(1, date_diff(charge_off_date_approx, issue_date, month))
        end as charge_off_mob
    from {{ ref('fct_loan') }}

),

spine as (

    select
        loan.*,
        mob
    from loan,
        unnest(generate_array(1, loan.term_months)) as mob

)

select
    {{ surrogate_key(['loan_id', 'mob']) }} as loan_month_key,
    loan_id,
    issue_date,
    concat(cast(extract(year from issue_date) as string), '-Q',
           cast(extract(quarter from issue_date) as string)) as issue_year_quarter,
    mob,
    date_add(issue_date, interval mob month) as as_of_date,

    -- has the loan aged at least `mob` months by the snapshot?
    mob <= observed_mob as is_observed,

    -- has the loan defaulted by this MOB?
    if(default_flag = 1 and charge_off_mob is not null and mob >= charge_off_mob, 1, 0)
        as default_flag_at_mob,

    -- measures carried for the cumulative-loss metric
    loan_amnt,
    if(default_flag = 1 and charge_off_mob is not null and mob >= charge_off_mob,
       net_chargeoff_amount, 0) as chargeoff_amount_at_mob

from spine
