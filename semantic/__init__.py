"""Governed semantic layer: metric definitions consumed by BI and the copilot."""
from .errors import SemanticError
from .layer import compare_cohorts, list_metrics, query_metric, roll_rate
from .metrics import METRICS
from .roll import ROLL_BUCKETS
from .windows import Window

__all__ = [
    "SemanticError",
    "Window",
    "METRICS",
    "ROLL_BUCKETS",
    "list_metrics",
    "query_metric",
    "compare_cohorts",
    "roll_rate",
]
