"""FastMCP server exposing the governed credit-risk tools over MCP (C3.5).

A deliberately *thin* wrapper: each tool below delegates straight to `copilot.tools` —
the exact same governed functions the Gemini copilot (C3.2) calls. So an MCP client
(Claude Desktop, Cursor, an internal agent) and the copilot consume the *same* semantic
layer: one governed definition, many consumers. No new logic and no free SQL — contract
violations still come back as structured ``{"error": {...}}`` data the client can read.

Run it over stdio (the transport MCP desktop clients speak):

    make mcp            # .venv-mcp/bin/python -m copilot.mcp_server

Needs its own venv (`.venv-mcp`, Python >=3.10) because the MCP SDK drops Python 3.9,
which the copilot/Streamlit venvs still use.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from copilot import tools

mcp = FastMCP(
    "credit-risk-cockpit",
    instructions=(
        "Governed credit-risk metrics over the public LendingClub accepted-loans book "
        "(2007-2018, snapshot 2019-03). Call list_metrics first to discover valid "
        "metric ids and windows. Cohorts are issue quarters like '2018-Q1'. Rates are "
        "fractions (0.12 = 12%). Every figure comes from the governed semantic layer — "
        "there is no free-form SQL."
    ),
)


@mcp.tool()
def list_metrics() -> list[dict]:
    """List the governed credit-risk metrics and the windows each one supports."""
    return tools.list_metrics()


@mcp.tool()
def query_metric(
    metric_id: str, window: str = "lifetime", cohort: str | None = None
) -> dict:
    """One governed metric across issue cohorts, or a single cohort, at a window.

    Cohorts are issue quarters like '2018-Q1' ('2018Q1' is also accepted). Omit `cohort`
    for every cohort. A contract violation returns ``{"error": {...}}`` to read and
    correct, not an exception.
    """
    return tools.query_metric(metric_id, window, cohort)


@mcp.tool()
def compare_cohorts(
    cohort_a: str, cohort_b: str, metric_id: str, window: str = "lifetime"
) -> dict:
    """Compare one governed metric between two issue cohorts at the same window."""
    return tools.compare_cohorts(cohort_a, cohort_b, metric_id, window)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
