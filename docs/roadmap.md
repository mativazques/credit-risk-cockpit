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
docs/roadmap.md first. Current state: checkpoint C0.1 is done (scaffold, dedicated GCP
project credit-risk-cockpit-2026 with billing + BigQuery/Cloud Storage APIs, Kaggle creds
in .env, kaggle installed in .venv). Start at the next unchecked checkpoint and go UP TO
checkpoint <PICK ONE, e.g. C1.5>. Stop at each checkpoint for me to review before
continuing — do NOT go past the ceiling I set. Small commits, English everywhere public,
git identity matirvazques@gmail.com.
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
  project + scripts bind-mounted (one source of truth), BigQuery via mounted ADC.
  `make airflow-start`. NOTE: code artifact complete + syntax/YAML-validated, but NOT
  run here — Docker daemon is down and the `astro` CLI isn't installed (both user-side).
  **STOP = orchestration story.**

## Phase 2 — Semantic layer
- [ ] **C2.1** Metric definitions as the single source of truth (`default_rate`,
  `cumulative_loss_rate`, `cohort_size`, `avg_dti`, `charge_off_rate`) + the `window` enum
  contract. BI reads these. **STOP = governed metrics.**

## Phase 3 — Agentic copilot
- [ ] **C3.1** The three tools (`list_metrics`, `query_metric`, `compare_cohorts`) as plain
  Python over the semantic layer; unit-tested; **no LLM yet**. **STOP = governed tools.**
- [ ] **C3.2** Gemini function-calling wiring (AI Studio API key from `.env`) + system
  prompt + FastAPI endpoint. **STOP = working NL copilot.**
- [ ] **C3.3** Hardening L1–L4: `max_output_tokens` + input caps, on-topic router
  (zero-token refusal off-topic), per-IP + global daily rate limit, answer cache.
  **STOP = abuse-safe copilot.**
- [ ] **C3.4** Streamlit chat panel integrated into the cockpit app. **STOP = full app
  locally.**
- [ ] **C3.5** *(optional)* Thin FastMCP wrapper exposing the same tool functions.
  **STOP = MCP differentiator.**

## Phase 4 — Polish & deploy
- [ ] **C4.1** Dockerfile; container runs locally.
- [ ] **C4.2** Terraform `main.tf` (GCS bucket, BQ dataset, Cloud Run, Artifact Registry,
  IAM); deploy to Cloud Run (`min-instances=0`, `max-instances` capped). **STOP = public
  live URL.**
- [ ] **C4.3** Finalize + test `make trim` / `make teardown`.
- [ ] **C4.4** README screenshots (manual) + copilot GIF + short write-up. **STOP =
  portfolio-ready.**

> *Billing kill-switch (hardening L5) is only needed if the copilot is ever moved from the
> AI Studio free tier to paid Vertex — see BLUEPRINT Cost & abuse hardening.*
