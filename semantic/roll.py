# semantic/roll.py
"""Governed delinquency roll rates — the transition-matrix counterpart to metrics.py.

A roll rate is P(next-month bucket = to_bucket | this-month bucket = from_bucket) by issue
cohort. Because it is a from->to matrix rather than the (cohort, value) single-metric shape
in metrics.py, it lives here as its own governed builder. SQL returns (issue_year_quarter,
value) so the execution layer reuses the same per-cohort plumbing as query_metric.

HONESTY: computed over the SYNTHETIC delinquency path (int_delinquency_path) — terminal
states are the loan's real outcome, the intermediate 30/60/90 walk is generated.
"""
from __future__ import annotations

from typing import Callable

from .errors import SemanticError

ROLL = "mart_roll_rates"

ROLL_BUCKETS: tuple[str, ...] = (
    "current", "dpd_30", "dpd_60", "dpd_90_plus", "charged_off", "paid",
)


def validate_bucket(name: str) -> None:
    if name not in ROLL_BUCKETS:
        raise SemanticError(
            "bucket_unknown",
            f"unknown delinquency bucket '{name}'; known: {list(ROLL_BUCKETS)}",
        )


def build_roll_rate_sql(from_bucket: str, to_bucket: str, mt: Callable[[str], str]) -> str:
    """SQL for the roll rate from one bucket to another, per issue cohort.

    Both buckets are validated by the caller (layer.roll_rate) before this runs; the
    literals are from the closed ROLL_BUCKETS set, so no injection surface.
    """
    return f"""
        select issue_year_quarter, roll_rate as value
        from {mt(ROLL)}
        where from_bucket = '{from_bucket}' and to_bucket = '{to_bucket}'
    """
