"""The three governed copilot tools (C3.1) — plain Python over the semantic layer.

No LLM here. These wrap `semantic.layer` for function-calling: the copilot (C3.2) hands
Gemini `TOOL_DECLARATIONS`, the model answers with a tool name + arguments, and
`dispatch` routes it. The one behavior that makes these *tools* rather than the raw
semantic functions: every contract violation is returned as **structured data**
(`{"error": {"code", "message"}}`) instead of raised, so the model can read the error and
self-correct on its next turn. The same functions are reused unchanged by the FastMCP
wrapper (C3.5).
"""
from __future__ import annotations

import re
from typing import Any, Callable

from semantic import (
    METRICS,
    SemanticError,
    Window,
    compare_cohorts as _compare_cohorts,
    list_metrics as _list_metrics,
    query_metric as _query_metric,
)

_METRIC_IDS = sorted(METRICS)
_WINDOW_VALUES = [w.value for w in Window]


_COHORT_RE = re.compile(r"^\s*((?:19|20)\d{2})\s*-?\s*[qQ]([1-4])\s*$")


def _normalize_cohort(cohort: str | None) -> str | None:
    """Canonicalize an issue cohort to the mart's 'YYYY-Qn' form.

    The model (or a user) writes '2015Q1', '2015 Q1', or lowercase just as readily as
    the canonical '2015-Q1'. Anything we can't parse is returned untouched so the
    semantic layer still reports it as cohort_unknown.
    """
    if cohort is None:
        return None
    m = _COHORT_RE.match(cohort)
    if not m:
        return cohort
    return f"{m.group(1)}-Q{m.group(2)}"


def _error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def _as_data(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a semantic-layer call, converting its structured error into data."""
    try:
        return fn(*args, **kwargs)
    except SemanticError as err:
        return err.as_dict()


def list_metrics() -> list[dict]:
    """Catalog of governed metrics and the windows each one supports."""
    return _list_metrics()


def query_metric(
    metric_id: str,
    window: str = Window.LIFETIME.value,
    cohort: str | None = None,
) -> dict:
    """One governed metric across issue cohorts (or a single cohort) at a window."""
    return _as_data(_query_metric, metric_id, window, _normalize_cohort(cohort))


def compare_cohorts(
    cohort_a: str,
    cohort_b: str,
    metric_id: str,
    window: str = Window.LIFETIME.value,
) -> dict:
    """One governed metric compared between two issue cohorts at the same window."""
    return _as_data(
        _compare_cohorts,
        _normalize_cohort(cohort_a),
        _normalize_cohort(cohort_b),
        metric_id,
        window,
    )


# --- function-calling contract handed to the model (C3.2) --------------------------

TOOL_DECLARATIONS: list[dict] = [
    {
        "name": "list_metrics",
        "description": (
            "List the governed credit-risk metrics available and the windows each one "
            "supports. Call this first to discover valid metric ids and windows."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "query_metric",
        "description": (
            "Query one governed metric across all issue cohorts, or a single cohort, at "
            "a given window. Returns per-cohort values."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "metric_id": {
                    "type": "string",
                    "enum": _METRIC_IDS,
                    "description": "Which governed metric to compute.",
                },
                "window": {
                    "type": "string",
                    "enum": _WINDOW_VALUES,
                    "description": "Months-on-book window; 'lifetime' for no MOB cap.",
                },
                "cohort": {
                    "type": "string",
                    "description": "Optional issue cohort like '2018-Q1'; omit for all cohorts.",
                },
            },
            "required": ["metric_id"],
        },
    },
    {
        "name": "compare_cohorts",
        "description": (
            "Compare one governed metric between two issue cohorts at the same window; "
            "returns both values and their difference."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "cohort_a": {"type": "string", "description": "First issue cohort, e.g. '2018-Q1'."},
                "cohort_b": {"type": "string", "description": "Second issue cohort, e.g. '2018-Q2'."},
                "metric_id": {
                    "type": "string",
                    "enum": _METRIC_IDS,
                    "description": "Which governed metric to compare.",
                },
                "window": {
                    "type": "string",
                    "enum": _WINDOW_VALUES,
                    "description": "Months-on-book window; 'lifetime' for no MOB cap.",
                },
            },
            "required": ["cohort_a", "cohort_b", "metric_id"],
        },
    },
]


# --- dispatch (route a model's tool call by name) ----------------------------------

TOOLS: dict[str, Callable[..., Any]] = {
    "list_metrics": list_metrics,
    "query_metric": query_metric,
    "compare_cohorts": compare_cohorts,
}


def dispatch(name: str, arguments: dict | None = None) -> Any:
    """Invoke a tool by name with the model's arguments, always returning JSON data.

    Unknown tool names and malformed argument sets (the model hallucinated a parameter)
    come back as structured errors, never exceptions — the copilot loop feeds them
    straight back to the model.
    """
    fn = TOOLS.get(name)
    if fn is None:
        return _error("tool_unknown", f"unknown tool '{name}'; known: {sorted(TOOLS)}")
    try:
        return fn(**(arguments or {}))
    except TypeError as exc:
        return _error("tool_bad_arguments", f"invalid arguments for tool '{name}': {exc}")
