"""On-topic router (C3.3 / L3) — a zero-token pre-filter.

Runs BEFORE the model call: if a question shows no sign of being about this book's
credit-risk metrics, it gets a canned refusal instead of burning quota. Deterministic
keyword match (the cheap version of the blueprint's keyword-or-embedding filter),
seeded from the metric registry and window vocabulary so it stays in sync with the
semantic layer. It deliberately errs toward answering — a stray on-topic word lets a
question through; the tool-constrained model is the second line of defense.
"""
from __future__ import annotations

import re

from semantic import Window
from semantic.metrics import METRICS

# Domain vocabulary. Metric ids + window values come straight from the semantic layer.
_KEYWORDS: set[str] = {
    "default", "loss", "charge", "chargeoff", "charge-off", "delinquen", "risk",
    "cohort", "vintage", "grade", "subgrade", "sub-grade", "dti", "debt", "income",
    "loan", "loans", "borrower", "portfolio", "book", "rate", "recover", "principal",
    "mob", "month", "months", "quarter", "cumulative", "hazard", "originat",
    *METRICS.keys(),
    *(w.value for w in Window),
}
_COHORT_RE = re.compile(r"\b(19|20)\d{2}\s*q[1-4]\b", re.IGNORECASE)  # e.g. 2018Q1


def is_on_topic(question: str) -> bool:
    text = question.lower()
    if _COHORT_RE.search(text):
        return True
    return any(kw in text for kw in _KEYWORDS)
