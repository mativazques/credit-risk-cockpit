"""Governed affordability stress — parametric breach rate over the DTI histogram.

Closed-form: an income shock `s` scales income to income*(1-s); with debt obligations
held fixed, stressed_dti = dti / (1-s), so a borrower breaches threshold `t` exactly
when their ORIGINAL dti > t*(1-s). The breach share is therefore a simple aggregation
of `mart_dti_histogram` (bucket = floor(dti), percent points, capped at 100) — no
loan-level scan.

HONESTY: the shock is a hypothetical scenario, not observed hardship; dti is measured
at origination (LendingClub percent-point scale, 0-100) and debt is held fixed in
nominal terms while income falls. Bucket resolution is 1 DTI point and the bucket
containing the cutoff counts as breaching (a <=1pp conservative overstatement).

The parameters are validated NUMBERS interpolated into SQL — never strings — so there
is no injection surface.
"""
from __future__ import annotations

from typing import Callable

from .errors import SemanticError

AFFORDABILITY_MART = "mart_dti_histogram"

MartTable = Callable[[str], str]  # name -> `project.dataset.name`


def validate_shock(shock: object) -> None:
    """An income shock is a fraction in [0, 1): 0 = baseline, 0.10 = 10% income drop."""
    if isinstance(shock, bool) or not isinstance(shock, (int, float)) or not 0 <= shock < 1:
        raise SemanticError(
            "shock_invalid",
            f"income shock must be a number in [0, 1) (fraction of income lost); got {shock!r}",
        )


def validate_threshold(threshold: object) -> None:
    """A DTI threshold in LendingClub percent points: (0, 100]."""
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < threshold <= 100
    ):
        raise SemanticError(
            "threshold_invalid",
            f"DTI threshold must be a number in (0, 100] percent points; got {threshold!r}",
        )


def build_breach_rate_sql(shock: float, threshold: float, mt: MartTable) -> str:
    """Breach share per cohort at the stressed cutoff t*(1-s). Params validated by the caller."""
    cutoff = float(threshold) * (1.0 - float(shock))
    return f"""
        select issue_year_quarter,
               safe_divide(sum(if(dti_bucket >= {cutoff}, n, 0)), sum(n)) as value
        from {mt(AFFORDABILITY_MART)}
        group by issue_year_quarter
    """
