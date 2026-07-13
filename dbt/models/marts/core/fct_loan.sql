-- Fact: one row per loan. FKs to dim_date (issue month), dim_loan_product,
-- dim_borrower; measures and risk flags for cohort / default analytics.

with loans as (

    select * from {{ ref('stg_loans') }}

),

status as (

    select * from {{ ref('int_loan_status_resolved') }}

)

select
    l.loan_id,

    -- foreign keys
    cast(format_date('%Y%m', l.issue_date) as int64) as issue_date_key,
    {{ surrogate_key(['l.grade', 'l.sub_grade', 'l.term_months', int_rate_band('l.int_rate')]) }} as loan_product_key,
    {{ surrogate_key(['l.home_ownership', 'l.emp_length', 'l.verification_status', 'l.addr_state']) }} as borrower_key,

    -- degenerate attributes
    l.issue_date,
    l.term_months,
    s.loan_status_std,
    s.default_flag,
    s.fully_paid_flag,
    s.is_right_censored,
    s.charge_off_date_approx,

    -- months of history observed at the snapshot (capped at term)
    least(
        date_diff(date('{{ var("snapshot_date") }}'), l.issue_date, month),
        l.term_months
    ) as observed_mob,

    -- measures
    l.loan_amnt,
    l.funded_amnt,
    l.installment,
    l.annual_inc,
    l.dti,
    l.int_rate,
    l.total_rec_prncp,
    l.out_prncp,
    l.recoveries

from loans l
join status s using (loan_id)
