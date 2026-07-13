-- Resolve loan status into risk flags and approximate the charge-off month.
-- The LendingClub snapshot carries only the FINAL status and no monthly payment
-- history, so the charge-off month is approximated from `last_pymnt_date`
-- (documented ±1-3 month noise). One row per loan.

with loans as (

    select * from {{ ref('stg_loans') }}

)

select
    loan_id,
    issue_date,
    last_pymnt_date,
    term_months,
    loan_status_std,

    -- the "bad" outcome for default_rate / vintage curves
    if(loan_status_std = 'charged_off', 1, 0) as default_flag,
    if(loan_status_std = 'fully_paid', 1, 0)  as fully_paid_flag,
    -- still-active loans are right-censored (no terminal outcome observed yet)
    if(loan_status_std = 'current', 1, 0)     as is_right_censored,

    -- approximate charge-off month (null unless charged off)
    if(loan_status_std = 'charged_off', last_pymnt_date, null) as charge_off_date_approx

from loans
