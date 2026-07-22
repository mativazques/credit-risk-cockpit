-- dbt/models/marts/analytics/mart_roll_rates.sql
{{ config(materialized='table') }}

-- Delinquency ROLL RATES: P(bucket next month = to_bucket | bucket this month = from_bucket),
-- by origination cohort. Built on the SYNTHETIC delinquency path (see int_delinquency_path):
-- terminal states are real, the 30/60/90 walk is generated. Small aggregate — safe to persist.
--
-- Only transitions with an OBSERVED next month are counted (next_bucket is not null), so no
-- right-censoring artefact leaks in.

with transitions as (

    select
        issue_year_quarter,
        bucket      as from_bucket,
        next_bucket as to_bucket
    from {{ ref('int_delinquency_path') }}
    where next_bucket is not null

),

from_totals as (

    select issue_year_quarter, from_bucket, count(*) as n_from
    from transitions
    group by issue_year_quarter, from_bucket

),

pairs as (

    select issue_year_quarter, from_bucket, to_bucket, count(*) as n_transition
    from transitions
    group by issue_year_quarter, from_bucket, to_bucket

)

select
    p.issue_year_quarter,
    p.from_bucket,
    p.to_bucket,
    f.n_from,
    p.n_transition,
    safe_divide(p.n_transition, f.n_from) as roll_rate
from pairs p
join from_totals f using (issue_year_quarter, from_bucket)
