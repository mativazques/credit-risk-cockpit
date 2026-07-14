"""Unit tests for the FastMCP server (C3.5) — no live MCP client, no BigQuery.

The MCP server is a *thin* wrapper: it must expose exactly the three governed tools and
delegate straight to `copilot.tools` (the same functions the Gemini copilot calls), so
any MCP client consumes the one governed semantic layer. These tests pin both the
exposed contract (tool names + schemas, generated from the signatures) and the
delegation, without standing up a transport or touching BigQuery.
"""
import asyncio

from copilot import mcp_server, tools


def _list_tools():
    return asyncio.run(mcp_server.mcp.list_tools())


def test_server_exposes_exactly_the_three_governed_tools():
    names = {t.name for t in _list_tools()}
    assert names == {"list_metrics", "query_metric", "compare_cohorts"}


def test_query_metric_tool_declares_its_parameters():
    qm = next(t for t in _list_tools() if t.name == "query_metric")
    props = qm.inputSchema["properties"]
    assert {"metric_id", "window", "cohort"} <= set(props)
    assert qm.inputSchema["required"] == ["metric_id"]


def test_compare_cohorts_tool_requires_both_cohorts_and_a_metric():
    cc = next(t for t in _list_tools() if t.name == "compare_cohorts")
    assert set(cc.inputSchema["required"]) == {"cohort_a", "cohort_b", "metric_id"}


def test_list_metrics_delegates_to_the_governed_tool(monkeypatch):
    monkeypatch.setattr(tools, "list_metrics", lambda: [{"id": "sentinel"}])
    assert mcp_server.list_metrics() == [{"id": "sentinel"}]


def test_query_metric_delegates_to_the_governed_tool(monkeypatch):
    seen = {}

    def _spy(*args):
        seen["args"] = args
        return {"ok": True}

    monkeypatch.setattr(tools, "query_metric", _spy)
    result = mcp_server.query_metric("default_rate", "lifetime", "2016-Q1")
    assert result == {"ok": True}
    assert seen["args"] == ("default_rate", "lifetime", "2016-Q1")


def test_compare_cohorts_delegates_to_the_governed_tool(monkeypatch):
    seen = {}

    def _spy(*args):
        seen["args"] = args
        return {"ok": True}

    monkeypatch.setattr(tools, "compare_cohorts", _spy)
    mcp_server.compare_cohorts("2015-Q1", "2016-Q1", "default_rate", "lifetime")
    assert seen["args"] == ("2015-Q1", "2016-Q1", "default_rate", "lifetime")
