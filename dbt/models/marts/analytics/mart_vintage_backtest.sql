{{ config(materialized='table') }}

-- Early-warning backtest: predict each cohort's MATURE (36-MOB) cumulative default
-- from its EARLY (12-MOB) rate via a seasoning multiplier, then score the prediction
-- against the realized value.
--
-- Method (honest and interview-defensible — a calibrated ratio, not ML):
--   * seasoning_multiplier = median(mature_cdr / early_cdr) over TRAIN cohorts only
--     (issued before 2014-Q1); applied out-of-sample to the HOLDOUT (2014-Q1+).
--   * Only fully-observed cohort points enter (right-censored cohorts are excluded,
--     so every "actual" is final, not a floor).
--   * Cohorts with early_cdr = 0 are excluded: a ratio predictor cannot scale zero.
--
-- Grain: issue_year_quarter (tiny table — one row per mature cohort).

with cohort_cdr as (

    -- cohort-level cumulative default rate at the two anchor MOBs, aggregated across
    -- terms exactly like the governed default_rate metric (sum/sum, fully_observed)
    select
        issue_year_quarter,
        mob,
        safe_divide(sum(cumulative_defaults), sum(cohort_size)) as cdr
    from {{ ref('mart_vintage_curves') }}
    where mob in (12, 36) and fully_observed
    group by issue_year_quarter, mob

),

joined as (

    select
        early.issue_year_quarter,
        early.cdr as early_cdr,
        mature.cdr as mature_cdr,
        -- lexicographic comparison is safe for the 'YYYY-Qn' format
        if(early.issue_year_quarter < '2014-Q1', 'train', 'holdout') as split
    from (select issue_year_quarter, cdr from cohort_cdr where mob = 12) as early
    inner join (select issue_year_quarter, cdr from cohort_cdr where mob = 36) as mature
        using (issue_year_quarter)
    where early.cdr > 0

),

mult as (

    -- book-wide median seasoning ratio, learned on the TRAIN split only
    select distinct
        percentile_cont(safe_divide(mature_cdr, early_cdr), 0.5) over ()
            as seasoning_multiplier
    from joined
    where split = 'train'

)

select
    joined.issue_year_quarter,
    joined.split,
    joined.early_cdr,
    joined.mature_cdr,
    mult.seasoning_multiplier,
    joined.early_cdr * mult.seasoning_multiplier as predicted_mature_cdr,
    joined.early_cdr * mult.seasoning_multiplier - joined.mature_cdr as backtest_error
from joined
cross join mult
