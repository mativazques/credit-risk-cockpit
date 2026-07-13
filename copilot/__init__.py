"""Agentic copilot: governed tools over the semantic layer, and (later) LLM wiring.

C3.1 ships the tool layer only — no LLM. C3.2 adds Gemini function-calling + FastAPI on
top of `TOOL_DECLARATIONS` and `dispatch`.
"""
from .tools import (
    TOOL_DECLARATIONS,
    TOOLS,
    compare_cohorts,
    dispatch,
    list_metrics,
    query_metric,
)

__all__ = [
    "TOOL_DECLARATIONS",
    "TOOLS",
    "dispatch",
    "list_metrics",
    "query_metric",
    "compare_cohorts",
]
