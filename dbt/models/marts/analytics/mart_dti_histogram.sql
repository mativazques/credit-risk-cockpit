{{ config(materialized='table') }}

-- Per-cohort DTI histogram — the base for the parametric affordability stress.
--
-- Why a histogram: the stress is closed-form (an income shock s turns a DTI threshold t
-- into a cutoff t*(1-s) on the ORIGINAL dti), so any (shock, threshold) breach rate is
-- just a share of this histogram. No loan-level scan at query time ($0 rule).
--
-- HONESTY: dti is measured at ORIGINATION (LendingClub percent points, 0-100 scale;
-- a few values exceed 100 and are capped into the 100 bucket). Any stress computed on
-- top of this is a hypothetical scenario, not observed hardship data.
--
-- Grain: issue_year_quarter x dti_bucket (bucket = floor(dti), width 1 DTI point).

with loan as (

    select
        concat(cast(extract(year from issue_date) as string), '-Q',
               cast(extract(quarter from issue_date) as string)) as issue_year_quarter,
        dti
    from {{ ref('fct_loan') }}
    where dti is not null and dti >= 0

)

select
    issue_year_quarter,
    least(cast(floor(dti) as int64), 100) as dti_bucket,
    count(*) as n
from loan
group by issue_year_quarter, dti_bucket
