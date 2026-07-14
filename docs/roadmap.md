# Roadmap — incremental checkpoints

> Build order as **small, independently-shippable checkpoints**. Each one ends in a
> commit and a state you could stop at without leaving things broken. Pick how far to go;
> don't run ahead of the checkpoint under review. This is the anti-"break things
> downstream" guardrail.
>
> Full design lives in [BLUEPRINT.md](../BLUEPRINT.md); the data-engineering readiness
> gate in [data-engineering.md](data-engineering.md).

## How to start a fresh session

Paste this, and set the ceiling to the checkpoint you want to reach:

```
Continue the credit-risk-cockpit. Read BLUEPRINT.md, docs/data-engineering.md and
docs/roadmap.md first. Current state: everything through C2.1 is DONE, committed AND
pushed to github.com/mativazques/credit-risk-cockpit (main). That means: data in
BigQuery (raw.lending_club_accepted, ~2.26M rows), full dbt star schema + vintage/cohort
marts (dataset analytics_marts), a Streamlit BI cockpit, a verified-runnable local
Airflow/Cosmos DAG, and the governed semantic layer (5 metrics + window contract).

Environment already set up: two venvs — .venv (dbt: dbt-core 1.9.10 / dbt-bigquery
1.9.2, protobuf>=6) and .venv-app (Streamlit, protobuf<6); never mix them. Astro CLI
installed (brew) + Docker for Airflow; `make airflow-start` boots it (dbt runs in an
in-image venv, Cosmos points at it). `make app` runs Streamlit at localhost:8501.
Kaggle creds + GCP_* in .env (gitignored); BigQuery auth via ADC.

The next unchecked checkpoint is C3.2 (Gemini function-calling wiring over the C3.1
governed tools in copilot/tools.py — AI Studio API key from .env, system prompt, FastAPI
endpoint). Start there and go UP TO checkpoint <PICK ONE, e.g. C3.3>. Stop at each
checkpoint for me to review before continuing — do NOT go past the ceiling I set. Small
commits, English everywhere public, git identity matirvazques@gmail.com.
```

Natural stopping points (each is a legit portfolio artifact on its own):
- **C1.5** — queryable vintage/cohort marts (pure analytics-eng piece).
- **C1.7** — the above + local Airflow/Cosmos orchestration.
- **C3.2** — a working NL copilot (function calling).
- **C4.2** — public live URL.
- **C4.4** — portfolio-ready (README + GIF).

---

## Phase 0 — Scaffold
- [x] **C0.1** Scaffold (`ingest.py`, folders, Makefile, `.env.example`), dedicated GCP
  project + billing + APIs, Kaggle creds verified, `.venv` with kaggle.
- [x] **C0.2** `make hydrate` → `raw.lending_club_accepted` loaded (2,260,668 rows; 33
  LendingClub summary-footer lines skipped via `max_bad_records`). Readiness-gate query
  (data-engineering §5) confirms all 11 needed columns present. **STOP = data lives in BigQuery.**

## Phase 1 — BI core
- [x] **C1.1** dbt project init (dbt-bigquery 1.9.2 / dbt-core 1.9.10); env-driven
  `profiles.yml` (not committed, `profiles.example.yml` is the template); `dbt debug`
  connects to BigQuery.
- [x] **C1.2** `stg_loans` staging (parse `Mon-YYYY` dates, `term_months`, standardize
  `loan_status`) + tests; the model referencing every metric-source column IS the
  readiness gate. Snapshot anchor (`2019-03`) added as a dbt var.
- [x] **C1.3** `fct_loan` (grain: loan) + dims (`dim_date`, `dim_borrower` — junk dim, no
  redacted member_id; `dim_loan_product`) + `int_loan_status_resolved` intermediate +
  surrogate-key/int-rate-band macros + relationship/uniqueness tests (23 pass).
- [x] **C1.4** `fct_loan_month` via date-spine (MOB 1..term); `default_flag_at_mob`;
  `is_observed` right-censoring flag; materialized as a VIEW (avoids persisting ~97M
  rows → $0 storage). Tests pass (10/10, incl. uniqueness on the full spine).
- [x] **C1.5** marts `mart_vintage_curves` (cohort x term x MOB triangle) +
  `mart_cohort_default` (cohort x grade summary) + dbt_utils tests (range +
  unique-combination) + `dbt docs`. Sanity-checked: monotonic vintage curves,
  grade A→G default 5.7%→45%. **STOP = analytics-eng portfolio piece (queryable marts).**
- [x] **C1.6** Streamlit cockpit (`app/`): vintage-curve line chart + cohort×grade
  heatmap, reading the marts via `@st.cache_data(ttl=3600)`. Own venv `.venv-app`
  (streamlit pins protobuf<6, dbt needs >=6). `make app` runs it; verified headless
  with Streamlit AppTest (KPIs + both tabs render, no exceptions).
  **STOP = visual BI demo (runs locally).**
- [x] **C1.7** Airflow local (Astro + Cosmos) in `airflow/`: `credit_risk_pipeline` DAG =
  `ingest` → Cosmos `DbtTaskGroup` (each dbt model its own task, tests after each). dbt
  project + scripts bind-mounted (one source of truth), BigQuery via mounted ADC. dbt
  runs in an isolated in-image venv (`dbt_venv`) so dbt-core and Airflow don't fight over
  shared deps; Cosmos points at it via `ExecutionConfig`. `make airflow-start`. VERIFIED:
  `astro dev start` boots all 4 containers, DAG parses with zero import errors, Cosmos
  renders 18 tasks (`ingest` + per-model run/test across every staging→mart model).
  **STOP = orchestration story.**

## Phase 2 — Semantic layer
- [x] **C2.1** `semantic/` — the five governed metrics (`default_rate`,
  `cumulative_loss_rate`, `cohort_size`, `avg_dti`, `charge_off_rate`) defined once over
  the marts, each declaring its valid `window`s (`mob_0_6`…`lifetime`). `list_metrics` /
  `query_metric` / `compare_cohorts` enforce the contract with structured `SemanticError`s
  (these become the C3.1 copilot tools). BI reads the catalog (governed-metrics expander).
  8 unit tests + live checks pass (monotonic curves; charge-off hazard peaks in year 2).
  **STOP = governed metrics.**

## Phase 3 — Agentic copilot
- [x] **C3.1** The three tools (`list_metrics`, `query_metric`, `compare_cohorts`) in
  `copilot/tools.py` — plain Python wrapping the semantic layer; contract violations come
  back as structured data (`{"error": {...}}`), never raised, so a model can self-correct;
  `TOOL_DECLARATIONS` (the function-calling schema for C3.2) + `dispatch(name, args)`
  routing. 12 unit tests, **no LLM**. **STOP = governed tools.**
- [x] **C3.2** Gemini function-calling wiring (`copilot/agent.py`, manual loop, automatic
  calling disabled so every call goes through governed `dispatch`) + system prompt +
  FastAPI `POST /ask`. Own venv `.venv-copilot` (google-genai off the Streamlit
  protobuf<6 pin). `GEMINI_API_KEY` from `.env`; `make api`. 9 unit tests, LLM faked.
  **STOP = working NL copilot** *(live smoke test pending the API key).*
- [x] **C3.3** Hardening L1–L4: `max_output_tokens=512` + input cap (`copilot/config.py`),
  on-topic router (`copilot/router.py`, zero-token refusal), per-IP token bucket + global
  daily cap (`copilot/ratelimit.py`), answer cache (`copilot/cache.py`), wired into
  `/ask` so only novel on-topic questions spend budget. 25 unit tests.
  **STOP = abuse-safe copilot.**
- [x] **C3.4** Streamlit chat panel (`app/chat.py`) as a third tab in the cockpit, talking
  to `/ask` via a thin `requests` client (`copilot/client.py`, no google-genai so the
  Streamlit venv stays clean); shows the governed tools each answer called. 5 client unit
  tests; headless AppTest confirms all three tabs render (chat input present, BI KPIs
  query BigQuery) with no exceptions. **STOP = full app locally** *(live chat needs the
  API key + `make api`).*
- [x] **C3.5** Thin FastMCP wrapper (`copilot/mcp_server.py`) exposing the same three
  governed tools over MCP (stdio) — delegates straight to `copilot/tools.py`, so an MCP
  client (Claude Desktop, Cursor) and the Gemini copilot share one governed semantic
  layer. Own venv `.venv-mcp` (Python 3.12; the MCP SDK drops 3.9). `make mcp` /
  `make mcp-test`; client wiring in [mcp.md](mcp.md). 6 unit tests; VERIFIED live over a
  real stdio handshake (list_tools + compare_cohorts against BigQuery, error-as-data
  preserved). **STOP = MCP differentiator.**

## Phase 4 — Polish & deploy
- [x] **C4.1** Dockerfile (single image, two isolated venvs — Streamlit protobuf<6 vs
  copilot protobuf>=6; `deploy/start.sh` runs uvicorn on 127.0.0.1:8000 + Streamlit on
  `$PORT`) + `.dockerignore`. Built and run locally end-to-end (copilot answered via the
  internal `/ask`).
- [x] **C4.2** Terraform owns the **serving** layer only (Artifact Registry, least-priv
  `cockpit-run` SA + BQ dataViewer/jobUser IAM, the Gemini secret container, the Cloud Run
  service, `allUsers` invoker); the data layer is left as bootstrapped. `min_instance=0`,
  `max` capped. Makefile runbook: `tf-init` → `tf-bootstrap` → `secret-push` →
  `image-push` (linux/amd64) → `deploy`. **DEPLOYED LIVE:**
  https://credit-risk-cockpit-kpn2dzalva-uc.a.run.app (Streamlit health 200; both
  processes boot clean in Cloud Run logs). **STOP = public live URL.**
- [x] **C4.3** `make teardown` → `terraform destroy` of the serving layer (data kept);
  `make trim` drops the raw layer. Both dry-run-verified.
- [ ] **C4.4** README screenshots (manual) + copilot GIF + short write-up. **STOP =
  portfolio-ready.**

> *Billing kill-switch (hardening L5) is only needed if the copilot is ever moved from the
> AI Studio free tier to paid Vertex — see BLUEPRINT Cost & abuse hardening.*
