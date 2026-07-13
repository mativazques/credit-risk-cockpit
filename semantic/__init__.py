"""Governed semantic layer: metric definitions consumed by BI and the copilot."""
from .errors import SemanticError
from .layer import compare_cohorts, list_metrics, query_metric
from .metrics import METRICS
from .windows import Window

__all__ = [
    "SemanticError",
    "Window",
    "METRICS",
    "list_metrics",
    "query_metric",
    "compare_cohorts",
]
