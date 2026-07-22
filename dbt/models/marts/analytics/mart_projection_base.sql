{{ config(materialized='table') }}

-- Projection anchor for the business-planning tab (Phase D).
--
-- One row per MOB 1..36: the cohort-size-weighted average cumulative loss-rate curve
-- over 36-month cohorts that are FULLY OBSERVED through MOB 36 (mature vintages only,
-- so the anchor is never right-censored). Scalar context is denormalized onto every
-- row (36-row table): the terminal (MOB-36) anchor loss rate and the originated
-- amount of the most recent mature cohort, which the scenario tool scales.
--
-- HONESTY: this is a scenario ANCHOR on public LendingClub curves, not a forecast of
-- a live book. Projections scale this historical shape; they do not model macro state.

with curves as (

    select *
    from {{ ref('mart_vintage_curves') }}
    where term_months = 36

),

mature_cohorts as (

    select issue_year_quarter
    from curves
    where mob = 36 and fully_observed

),

anchor_curve as (

    select
        c.mob,
        safe_divide(
            sum(c.cumulative_loss_rate * c.cohort_size),
            sum(c.cohort_size)
        ) as anchor_cumulative_loss_rate
    from curves c
    inner join mature_cohorts m using (issue_year_quarter)
    where c.mob between 1 and 36
    group by c.mob

),

terminal_rate as (

    select anchor_cumulative_loss_rate as anchor_terminal_loss_rate
    from anchor_curve
    where mob = 36

),

volume_anchor as (

    select c.originated_amount as baseline_originated
    from curves c
    where c.issue_year_quarter = (select max(issue_year_quarter) from mature_cohorts)
      and c.mob = 1

)

select
    a.mob,
    a.anchor_cumulative_loss_rate,
    t.anchor_terminal_loss_rate,
    v.baseline_originated
from anchor_curve a
cross join terminal_rate t
cross join volume_anchor v
