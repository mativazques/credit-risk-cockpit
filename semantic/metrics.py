"""The governed metric registry — the single source of truth.

Each metric is defined ONCE here (definition, unit, which windows are valid, and the
SQL that computes it over the marts). BI and the copilot both read this registry, so a
metric means exactly the same thing everywhere. All SQL returns rows of
`(issue_year_quarter, value)` at the cohort grain.

Honesty caveats carried from the marts:
  * charge-off month is approximated from last_pymnt_date (±1-3 months);
  * windowed rates use only `fully_observed` cohort points (right-censored points are
    excluded, not silently understated);
  * `charge_off_rate` is the conditional 12-MOB default hazard given survival — a
    defensible approximation of "charged-off / active", valid from mob_0_12 onward.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .windows import WINDOW_MOB, Window

# Mart names; the caller supplies a resolver that fully-qualifies them.
VINTAGE = "mart_vintage_curves"
COHORT = "mart_cohort_default"

MartTable = Callable[[str], str]  # name -> `project.dataset.name`

_ALL_WINDOWS = tuple(Window)


@dataclass(frozen=True)
class Metric:
    id: str
    label: str
    description: str
    unit: str  # "rate" | "count" | "ratio"
    valid_windows: tuple[Window, ...]
    build_sql: Callable[[Window, MartTable], str]

    def supports(self, window: Window) -> bool:
        return window in self.valid_windows


# --- SQL builders (one per metric) -----------------------------------------------

def _cohort_size_sql(_w: Window, mt: MartTable) -> str:
    return f"""
        select issue_year_quarter, sum(cohort_size) as value
        from {mt(COHORT)}
        group by issue_year_quarter
    """


def _avg_dti_sql(_w: Window, mt: MartTable) -> str:
    return f"""
        select issue_year_quarter,
               safe_divide(sum(avg_dti * cohort_size), sum(cohort_size)) as value
        from {mt(COHORT)}
        group by issue_year_quarter
    """


def _default_rate_sql(w: Window, mt: MartTable) -> str:
    if w is Window.LIFETIME:
        return f"""
            select issue_year_quarter,
                   safe_divide(sum(n_defaults), sum(cohort_size)) as value
            from {mt(COHORT)}
            group by issue_year_quarter
        """
    mob = WINDOW_MOB[w]
    return f"""
        select issue_year_quarter,
               safe_divide(sum(cumulative_defaults), sum(cohort_size)) as value
        from {mt(VINTAGE)}
        where mob = {mob} and fully_observed
        group by issue_year_quarter
    """


def _cumulative_loss_rate_sql(w: Window, mt: MartTable) -> str:
    if w is Window.LIFETIME:
        return f"""
            select issue_year_quarter,
                   safe_divide(sum(lifetime_loss_rate * originated_amount),
                               sum(originated_amount)) as value
            from {mt(COHORT)}
            group by issue_year_quarter
        """
    mob = WINDOW_MOB[w]
    return f"""
        select issue_year_quarter,
               safe_divide(sum(cumulative_chargeoff_amount),
                           sum(originated_amount)) as value
        from {mt(VINTAGE)}
        where mob = {mob} and fully_observed
        group by issue_year_quarter
    """


def _charge_off_rate_sql(w: Window, mt: MartTable) -> str:
    # Conditional 12-MOB default hazard given survival to (mob-12):
    #   (cdr[mob] - cdr[mob-12]) / (1 - cdr[mob-12]).
    # For mob_0_12 the baseline is origination (cdr=0), handled by the left join.
    mob = WINDOW_MOB[w]
    prev = mob - 12
    return f"""
        with a as (
            select issue_year_quarter,
                   safe_divide(sum(cumulative_defaults), sum(cohort_size)) as cdr
            from {mt(VINTAGE)}
            where mob = {mob} and fully_observed
            group by issue_year_quarter
        ),
        b as (
            select issue_year_quarter,
                   safe_divide(sum(cumulative_defaults), sum(cohort_size)) as cdr
            from {mt(VINTAGE)}
            where mob = {prev} and fully_observed
            group by issue_year_quarter
        )
        select a.issue_year_quarter,
               safe_divide(a.cdr - coalesce(b.cdr, 0),
                           1 - coalesce(b.cdr, 0)) as value
        from a left join b using (issue_year_quarter)
    """


METRICS: dict[str, Metric] = {
    m.id: m
    for m in [
        Metric(
            id="cohort_size",
            label="Cohort size",
            description="Number of loans originated in the cohort.",
            unit="count",
            valid_windows=(Window.LIFETIME,),
            build_sql=_cohort_size_sql,
        ),
        Metric(
            id="avg_dti",
            label="Average DTI",
            description="Cohort-size-weighted average debt-to-income at application.",
            unit="ratio",
            valid_windows=(Window.LIFETIME,),
            build_sql=_avg_dti_sql,
        ),
        Metric(
            id="default_rate",
            label="Default rate",
            description="Charged-off loans divided by cohort size, by window.",
            unit="rate",
            valid_windows=_ALL_WINDOWS,
            build_sql=_default_rate_sql,
        ),
        Metric(
            id="cumulative_loss_rate",
            label="Cumulative loss rate",
            description="Cumulative net charge-off principal divided by originated, by window.",
            unit="rate",
            valid_windows=_ALL_WINDOWS,
            build_sql=_cumulative_loss_rate_sql,
        ),
        Metric(
            id="charge_off_rate",
            label="Charge-off rate (12-MOB hazard)",
            description="Conditional 12-month default rate given survival; valid from mob_0_12.",
            unit="rate",
            valid_windows=(
                Window.MOB_0_12,
                Window.MOB_0_24,
                Window.MOB_0_36,
                Window.MOB_0_60,
            ),
            build_sql=_charge_off_rate_sql,
        ),
    ]
}
