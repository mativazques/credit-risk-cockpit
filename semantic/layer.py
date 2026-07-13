"""Execution layer over the governed metric registry.

Plain Python (no LLM). These functions are what BI calls today and what the copilot's
governed tools (C3.1: list_metrics / query_metric / compare_cohorts) will wrap
one-to-one. Every call validates against the registry and the window contract and
raises a structured `SemanticError` on violation — never raw SQL or a stack trace.
"""
from __future__ import annotations

import os
from functools import lru_cache

from google.cloud import bigquery

from .errors import SemanticError
from .metrics import METRICS, Metric
from .windows import Window, parse_window

_DBT_DATASET = os.environ.get("BQ_DBT_DATASET", "analytics")
_MARTS_DATASET = f"{_DBT_DATASET}_marts"
_PROJECT = os.environ.get("GCP_PROJECT")


def _marts_table(name: str) -> str:
    return f"`{_PROJECT}.{_MARTS_DATASET}.{name}`"


@lru_cache(maxsize=1)
def _client() -> bigquery.Client:
    return bigquery.Client(project=_PROJECT)


def _resolve_metric(metric_id: str) -> Metric:
    metric = METRICS.get(metric_id)
    if metric is None:
        raise SemanticError(
            "metric_unknown",
            f"unknown metric '{metric_id}'; known: {sorted(METRICS)}",
        )
    return metric


def _resolve_window(metric: Metric, window: str | Window) -> Window:
    try:
        w = parse_window(window)
    except ValueError as exc:
        raise SemanticError("window_unknown", str(exc)) from exc
    if not metric.supports(w):
        raise SemanticError(
            "window_unsupported",
            f"metric '{metric.id}' does not support window '{w.value}'; "
            f"valid: {[x.value for x in metric.valid_windows]}",
        )
    return w


def list_metrics() -> list[dict]:
    """Catalog of governed metrics and their valid windows."""
    return [
        {
            "id": m.id,
            "label": m.label,
            "description": m.description,
            "unit": m.unit,
            "valid_windows": [w.value for w in m.valid_windows],
        }
        for m in METRICS.values()
    ]


def query_metric(
    metric_id: str,
    window: str | Window = Window.LIFETIME,
    cohort: str | None = None,
) -> dict:
    """Resolve a governed metric to per-cohort values (or one cohort's value).

    Raises SemanticError (structured) on an unknown metric or an invalid window.
    """
    metric = _resolve_metric(metric_id)
    w = _resolve_window(metric, window)

    sql = metric.build_sql(w, _marts_table)
    rows = {r["issue_year_quarter"]: r["value"] for r in _client().query(sql).result()}

    if cohort is not None:
        if cohort not in rows:
            raise SemanticError(
                "cohort_unknown",
                f"no value for cohort '{cohort}' at window '{w.value}' "
                f"(it may be right-censored at this window)",
            )
        results = [{"cohort": cohort, "value": rows[cohort]}]
    else:
        results = [
            {"cohort": c, "value": rows[c]} for c in sorted(rows) if rows[c] is not None
        ]

    return {
        "metric": metric.id,
        "unit": metric.unit,
        "window": w.value,
        "results": results,
    }


def compare_cohorts(
    cohort_a: str,
    cohort_b: str,
    metric_id: str,
    window: str | Window = Window.LIFETIME,
) -> dict:
    """Compare one governed metric between two cohorts at the same window."""
    a = query_metric(metric_id, window, cohort_a)["results"][0]["value"]
    b = query_metric(metric_id, window, cohort_b)["results"][0]["value"]
    return {
        "metric": metric_id,
        "window": parse_window(window).value,
        "cohort_a": {"cohort": cohort_a, "value": a},
        "cohort_b": {"cohort": cohort_b, "value": b},
        "difference": None if a is None or b is None else a - b,
    }
