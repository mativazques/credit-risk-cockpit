-- Vintage default curves: cumulative default- and loss-rate by
-- (issue cohort x term x month-on-book). This is the classic vintage triangle
-- that answers "how does each origination cohort's risk develop as it ages?".
--
-- Grain: issue_year_quarter x term_months x mob.
--   * term_months is in the grain so 36- and 60-month loans don't create a
--     discontinuity at MOB 36 (their at-risk populations differ). BI can filter.
--   * cohort_size / originated_amount are constant across mob within a cohort x term
--     (every loan in the cohort has a spine row for mob 1..term), so the denominators
--     are stable and the cumulative rates are monotonic.
--
-- Honesty: `fully_observed` is true only where EVERY loan in the cohort has aged at
-- least `mob` months by the 2019-03 snapshot. Points where it is false are
-- right-censored — plot them dashed / drop them, don't read them as final.

with loan_month as (

    select * from {{ ref('fct_loan_month') }}

)

select
    issue_year_quarter,
    term_months,
    mob,

    -- stable denominators (constant across mob within cohort x term)
    count(*)                              as cohort_size,
    sum(loan_amnt)                        as originated_amount,

    -- cumulative numerators (monotonic in mob)
    sum(default_flag_at_mob)              as cumulative_defaults,
    sum(chargeoff_amount_at_mob)          as cumulative_chargeoff_amount,

    -- the governed rates
    safe_divide(sum(default_flag_at_mob), count(*))
        as cumulative_default_rate,
    safe_divide(sum(chargeoff_amount_at_mob), sum(loan_amnt))
        as cumulative_loss_rate,

    -- right-censoring flag: true only if the whole cohort is observed at this mob
    logical_and(is_observed)              as fully_observed

from loan_month
group by issue_year_quarter, term_months, mob
