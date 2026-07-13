"""Unit tests for the copilot tool layer (C3.1) — no LLM, no BigQuery.

These tools wrap the semantic layer for LLM function-calling. The one behavior that
distinguishes a tool from the raw semantic function: a contract violation must come back
as *structured data* the model can read and self-correct on, never as a raised
exception. Contract checks (unknown metric / invalid window / unknown tool / bad args)
all run before any SQL, so they are fully testable offline.
"""
import pytest

from semantic import Window
from semantic.metrics import METRICS

import copilot
from copilot import tools


# --- declarations (the function-calling contract handed to Gemini in C3.2) ---------

def test_declarations_cover_exactly_the_three_tools():
    names = {d["name"] for d in tools.TOOL_DECLARATIONS}
    assert names == {"list_metrics", "query_metric", "compare_cohorts"}


def test_query_metric_declaration_enumerates_metrics_and_windows_from_the_registry():
    decl = next(d for d in tools.TOOL_DECLARATIONS if d["name"] == "query_metric")
    props = decl["parameters"]["properties"]
    assert set(props["metric_id"]["enum"]) == set(METRICS)
    assert props["window"]["enum"] == [w.value for w in Window]
    assert decl["parameters"]["required"] == ["metric_id"]


def test_compare_cohorts_declaration_requires_both_cohorts_and_a_metric():
    decl = next(d for d in tools.TOOL_DECLARATIONS if d["name"] == "compare_cohorts")
    assert decl["parameters"]["required"] == ["cohort_a", "cohort_b", "metric_id"]


# --- list_metrics: pure registry, safe to call for real ----------------------------

def test_list_metrics_tool_returns_the_catalog():
    result = tools.list_metrics()
    assert {m["id"] for m in result} == set(METRICS)


# --- errors come back as data, not exceptions --------------------------------------

def test_query_metric_tool_returns_error_as_data_for_unknown_metric():
    result = tools.query_metric("made_up_metric")
    assert result["error"]["code"] == "metric_unknown"


def test_query_metric_tool_returns_error_as_data_for_unsupported_window():
    # avg_dti is an application-time attribute: lifetime only.
    result = tools.query_metric("avg_dti", window="mob_0_12")
    assert result["error"]["code"] == "window_unsupported"


def test_compare_cohorts_tool_returns_error_as_data_for_unknown_metric():
    result = tools.compare_cohorts("2018Q1", "2018Q2", "made_up_metric")
    assert result["error"]["code"] == "metric_unknown"


# --- success passes the semantic result straight through (no BigQuery in the test) --

def test_query_metric_tool_passes_semantic_result_through(monkeypatch):
    sentinel = {"metric": "default_rate", "unit": "rate", "window": "lifetime", "results": []}
    monkeypatch.setattr(tools, "_query_metric", lambda *a, **k: sentinel)
    assert tools.query_metric("default_rate") is sentinel


# --- dispatch: route a model's tool call by name -----------------------------------

def test_dispatch_routes_to_the_named_tool():
    result = tools.dispatch("list_metrics", {})
    assert {m["id"] for m in result} == set(METRICS)


def test_dispatch_unknown_tool_returns_structured_error():
    result = tools.dispatch("drop_table", {})
    assert result["error"]["code"] == "tool_unknown"


def test_dispatch_bad_arguments_returns_structured_error():
    result = tools.dispatch("query_metric", {"not_a_param": 1})
    assert result["error"]["code"] == "tool_bad_arguments"


def test_package_reexports_the_public_tool_surface():
    assert copilot.dispatch is tools.dispatch
    assert copilot.TOOL_DECLARATIONS is tools.TOOL_DECLARATIONS
