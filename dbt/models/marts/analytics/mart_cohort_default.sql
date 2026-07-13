-- Cohort default summary: one row per (issue cohort x grade) with lifetime
-- outcome metrics at the loan grain. This is the cohort heatmap source
-- (cohort on one axis, grade on the other) and the home of the ✅ direct metrics
-- cohort_size / default_rate / avg_dti.
--
-- Grain: issue_year_quarter x grade.
--
-- Honesty: `default_rate` and `lifetime_loss_rate` are lifetime-to-snapshot figures.
-- Cohorts from 2017-2018 are still seasoning at the 2019-03 snapshot (many loans
-- are `current`, captured in `share_still_current`), so their realized rates are
-- floors, not final. Older cohorts (<=2016) are effectively fully seasoned.

with loans as (

    select
        f.loan_id,
        f.issue_date,
        f.default_flag,
        f.fully_paid_flag,
        f.is_right_censored,
        f.dti,
        f.loan_amnt,
        f.funded_amnt,
        f.total_rec_prncp,
        f.recoveries,
        p.grade
    from {{ ref('fct_loan') }} f
    join {{ ref('dim_loan_product') }} p using (loan_product_key)

)

select
    concat(cast(extract(year from issue_date) as string), '-Q',
           cast(extract(quarter from issue_date) as string)) as issue_year_quarter,
    grade,

    count(*)                                          as cohort_size,
    sum(default_flag)                                 as n_defaults,
    sum(fully_paid_flag)                              as n_fully_paid,
    sum(is_right_censored)                            as n_still_current,

    safe_divide(sum(default_flag), count(*))          as default_rate,
    safe_divide(sum(is_right_censored), count(*))     as share_still_current,
    avg(dti)                                          as avg_dti,

    sum(loan_amnt)                                    as originated_amount,
    sum(greatest(0, funded_amnt - total_rec_prncp - recoveries))
        as net_chargeoff_amount,
    safe_divide(
        sum(if(default_flag = 1,
               greatest(0, funded_amnt - total_rec_prncp - recoveries), 0)),
        sum(loan_amnt)
    )                                                 as lifetime_loss_rate

from loans
group by issue_year_quarter, grade
