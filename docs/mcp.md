# MCP server — governed credit-risk tools for any agent (C3.5)

The same three governed tools the Gemini copilot calls (`list_metrics`, `query_metric`,
`compare_cohorts`) are also exposed over the **Model Context Protocol (MCP)**. So any
MCP-capable client — Claude Desktop, Cursor, an internal agent — can query the book's
credit risk through the *same* governed semantic layer: one definition, many consumers,
no free-form SQL.

The server ([`copilot/mcp_server.py`](../copilot/mcp_server.py)) is a thin FastMCP
wrapper — it adds no logic, it just re-exports `copilot/tools.py` over stdio. Contract
violations still come back as structured `{"error": {...}}` data the client can read and
self-correct on.

## Why its own venv

The MCP SDK requires Python ≥3.10; the copilot and Streamlit venvs are on 3.9. So the
server lives in `.venv-mcp`:

```bash
python3.12 -m venv .venv-mcp
.venv-mcp/bin/pip install -r copilot/requirements-mcp.txt
```

## Run it

```bash
make mcp        # .venv-mcp/bin/python -m copilot.mcp_server  (stdio transport)
make mcp-test   # unit tests (no live client, no BigQuery)
```

It reads the marts from BigQuery via ADC, so `GCP_PROJECT` must be set and
`gcloud auth application-default login` done — same as the rest of the project.

## Wire it into Claude Desktop

Add this to `~/Library/Application Support/Claude/claude_desktop_config.json` (use
absolute paths; the client spawns the server with a minimal env, so pass `GCP_PROJECT`
explicitly):

```json
{
  "mcpServers": {
    "credit-risk-cockpit": {
      "command": "/ABSOLUTE/PATH/credit-risk-cockpit/.venv-mcp/bin/python",
      "args": ["-m", "copilot.mcp_server"],
      "cwd": "/ABSOLUTE/PATH/credit-risk-cockpit",
      "env": { "GCP_PROJECT": "your-gcp-project" }
    }
  }
}
```

Then ask, in a normal Claude chat: *"Compare the default rate of the 2015-Q1 vs 2016-Q1
cohorts."* Claude calls `compare_cohorts`, which resolves against the governed marts and
answers with the real figures — no SQL, no invented numbers.
