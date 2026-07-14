# Credit-Risk Cockpit

A credit-risk and affordability cockpit for a consumer-lending book: vintage default
curves and cohort heatmaps in BI, plus an agentic copilot that answers risk questions in
natural language over a governed dbt semantic layer.

**▶ Live demo:** https://credit-risk-cockpit-kpn2dzalva-uc.a.run.app
_(Cloud Run, scale-to-zero — the first request after a cold start takes a few seconds to wake the container.)_

**Interview story:** this project proves ownership of cohort/vintage credit analytics
(the day-to-day work) and the differentiator — a governed text-to-metric agent that
answers "why did the Q3-2021 cohort's default rate lift vs Q2?" by calling typed MCP
tools over shared metric definitions, not by writing raw SQL against live tables.

---

## What It Does

- **Vintage curves + cohort heatmaps (BI standing views):** dbt-powered marts render
  cumulative default rates by months-on-book and cohort quarter — the core view a risk
  manager opens every morning.
- **Natural-language copilot:** ask "why did Q3-2021 lift?" and the agent decomposes the
  question, queries the same governed metrics as the BI layer, compares cohorts, and
  narrates the driver. Governed text-to-metric, not raw text-to-SQL.
- **Shared semantic layer:** `default_rate`, `cumulative_loss_rate`, `cohort_size`,
  `avg_dti`, `charge_off_rate` — defined once in dbt, consumed identically by the BI
  dashboard and the agentic copilot.

---

## The Business Case (Illustrative)

Loss-avoidance-as-insurance framing: the cockpit shortens detection lead-time; even a
few basis points of avoided loss on the book it influences pays for itself. The model
uses a pilot anchor (one product line, ~€200M receivables) that grows via a deployment
ladder.

**Pilot base case (5 bp detection lift on €200M):** ~€100k/yr hard benefit. Payback
from partial rollout (€600M influenced, 5 bp): ~€300k hard + soft, payback ≈ 4-5
months, Year-1 ROI ~2-3x. Worst-case pilot (2 bp, hard only): €40k vs ~€0 demo run
cost — still positive from year 2 on run cost alone.

See [BLUEPRINT.md](BLUEPRINT.md) for the full rollout ladder, sensitivity table, and TCO
breakdown. Public dataset, stated assumptions, illustrative — not a live book.

---

## Screenshots / Demo

Try it live: **https://credit-risk-cockpit-kpn2dzalva-uc.a.run.app**

**Vintage curves** — cumulative default rate by month-on-book, one line per issue
cohort. Right-censored points are hidden by default so cohorts are compared on equal
footing.

![Vintage curves: cumulative default rate by month on book, per issue cohort](docs/img/dashboard.png)

**Cohort × grade heatmap** — default rate across issue quarter and LendingClub credit
grade over the full 2.26M-loan book, with the governed metric definitions one click away.

![Cohort-by-grade heatmap: default rate across issue quarter and credit grade](docs/img/cohort-heatmap.png)

**Ask the copilot** — a natural-language question answered only from the governed tools
(`list_metrics`, `query_metric`, `compare_cohorts`). Every answer states the numbers,
the driver, and which governed tool it called, so each figure is traceable back to a
single metric definition — no free-form SQL, no invented numbers.

![Copilot comparing two cohorts' default rates and naming the governed tool it called](docs/img/copilot.gif)

---

## Architecture

```
                    ┌──────────── Airflow (orchestration) ────────────┐
                    │  ingest → dbt run → dbt test  (via Cosmos)       │
                    └──────────────────────┬──────────────────────────┘
                                           ▼
Kaggle CSV → GCS (raw) → BigQuery (raw)
                          → dbt (staging → intermediate → marts + semantic layer)
                          → Streamlit  (BI cockpit + chat)
                          → FastAPI + Gemini (Vertex AI) + MCP  (agentic copilot)
                          → Cloud Run (deploy, min-instances=0)   ·   Terraform (IaC)
```

dbt models are rendered as individual Airflow tasks via **astronomer-cosmos**, so the
DAG mirrors the dbt lineage graph — the modern pattern NL/DE data teams expect.

**Deploy shape.** The whole app ships as **one Cloud Run container** running two isolated
Python venvs: Streamlit pins `protobuf<6` while the copilot's `google-genai` needs `>=6`,
so they can't share an environment. `deploy/start.sh` runs the copilot (FastAPI + Gemini)
on an internal `127.0.0.1:8000` and Streamlit on the public `$PORT`; the chat panel talks
to the copilot over that loopback. Terraform owns only the **serving** layer (Artifact
Registry, a least-privilege runtime service account with read-only BigQuery access, the
Gemini secret, the Cloud Run service). The **data** layer (GCS raw + BigQuery datasets) is
left as bootstrapped by the pipeline, so re-declaring it in IaC can't destroy loaded data.
The service is `min-instances=0` (scale-to-zero → $0 idle) with `max-instances` capped.

---

## Stack

Python · SQL · BigQuery · dbt · Airflow (Cosmos) · FastAPI · Gemini (Vertex AI) · MCP · Streamlit · Cloud Run · GCP · Terraform

---

## How to Run

### Prerequisites

- A free [Kaggle account](https://www.kaggle.com) → *Account → Create New Token* to get
  `KAGGLE_USERNAME` / `KAGGLE_KEY`.
- A GCP project on your own account, with the **BigQuery** and **Cloud Storage** APIs
  enabled. Create the GCS bucket and BigQuery dataset in a **US region** (`us-central1`)
  so they stay inside the GCS 5 GB and BigQuery 10 GB Always-Free tiers.
- `cp .env.example .env` and fill in the values.

### Phase 0 — Ingestion (Kaggle → GCS → BigQuery)

The ingestion script is env-driven and runs identically in three places. There is no
native Kaggle→GCS transfer, so the ~1.4 GB CSV is downloaded once, then pushed to GCS
and loaded into BigQuery.

**Recommended — [Google Cloud Shell](https://shell.cloud.google.com)** (free, keeps the
CSV off your laptop; `gcloud`/`gsutil` are pre-installed):

```bash
git clone https://github.com/mativazques/credit-risk-cockpit && cd credit-risk-cockpit
pip install -r scripts/requirements.txt
cp .env.example .env   # then edit .env
python scripts/ingest.py
```

**Or locally** — same commands. **Or in Phase 1+** the same script is wrapped by a Cloud
Run Job / Airflow task. The script is idempotent: it skips the Kaggle download if the
object already exists in GCS and replaces the BigQuery table on load.

**Cost:** GCS 1.4 GB and the BigQuery raw table sit inside the Always-Free tiers → $0/mo.

### Environments

The stack needs **four isolated venvs** because the tools have conflicting pins — each is
created once and the `Makefile` targets point at it. This is the same protobuf/Python
split that the single deploy container reproduces.

```bash
python3   -m venv .venv         && .venv/bin/pip install -r dbt/requirements.txt        # dbt (protobuf>=6)
python3   -m venv .venv-app     && .venv-app/bin/pip install -r app/requirements.txt     # Streamlit (protobuf<6)
python3   -m venv .venv-copilot && .venv-copilot/bin/pip install -r copilot/requirements.txt  # FastAPI + Gemini (protobuf>=6)
python3.12 -m venv .venv-mcp    && .venv-mcp/bin/pip install -r copilot/requirements-mcp.txt   # MCP SDK (needs Python ≥3.10)
```

### Phase 1–2 — dbt models + semantic layer

```bash
make dbt-build        # run + test the whole DAG in lineage order (SELECT=<model> to target one)
make dbt-docs         # generate the dbt docs site
make airflow-start    # optional: local Airflow (Astro + Cosmos) renders each model as a task
```

BigQuery auth is via ADC (`gcloud auth application-default login`). `dbt` reads
`GCP_PROJECT` / `BQ_DBT_DATASET` / `BQ_LOCATION` from `.env`; the marts land in
`<BQ_DBT_DATASET>_marts`.

### Phase 3 — BI cockpit + copilot

```bash
make app              # Streamlit cockpit at localhost:8501 (vintage curves, heatmap, chat tab)
make api              # copilot FastAPI at localhost:8000 (needs GEMINI_API_KEY in .env)
make mcp              # MCP server (stdio) exposing the same governed tools — see docs/mcp.md
make copilot-test     # copilot + semantic unit tests (no LLM, no BigQuery)
make mcp-test         # MCP server unit tests
```

The chat tab calls the copilot API, so run `make api` alongside `make app` for live Q&A.
The copilot only spends tokens on **novel, on-topic** questions (on-topic router +
per-IP/global token caps + answer cache); off-topic questions are refused at zero cost.

### Phase 4 — Container + deploy to Cloud Run

```bash
make docker-build     # build the single image (two venvs) and run it locally
make tf-init tf-bootstrap secret-push image-push deploy   # full deploy runbook → prints the public URL
```

See [terraform/README.md](terraform/README.md) for the per-step deploy runbook and the
cost breakdown. `make teardown` destroys the serving layer (data kept); `make trim` drops
the heavy raw layer while keeping the marts (zero-storage resting state).

---

## Data

LendingClub loan data 2007–2018 from Kaggle
([wordsforthewise/lending-club](https://www.kaggle.com/datasets/wordsforthewise/lending-club)),
licensed **CC0 1.0 Public Domain**, ~2.26M accepted loans.

Vintage and months-on-book metrics are **derived** from the loan-level snapshot via
`issue_d` + `last_pymnt_d` (no monthly payment time series exists in the dataset;
charge-off month is approximated — stated transparently). 2017–2018 originations are
right-censored at the snapshot date and labeled as such.

No proprietary data. Raw CSV not committed to the repo (requires a free Kaggle account
to download). All numbers illustrative with stated assumptions.

---

## Dimensional Model

`fct_loan` (grain: loan) and `fct_loan_month` (grain: loan x month-on-book, generated
via a dbt date-spine cross-joined against MOB integers 1..term) form the core facts.
Dimensions: `dim_borrower`, `dim_date`, `dim_loan_product` (grade, sub_grade,
term_months, int_rate_band). Marts: `mart_vintage_curves`, `mart_cohort_default`.
Semantic-layer metrics (`default_rate`, `cumulative_loss_rate`, `cohort_size`, `avg_dti`,
`charge_off_rate`) are defined once and consumed by both the BI layer and the agentic
copilot.

---

## Status

| Phase | Description | State |
| :--- | :--- | :--- |
| Phase 0 | Scaffold: repo, .gitignore, ingestion → BigQuery (~2.26M rows) | ✅ Done |
| Phase 1 | BI core: dbt star schema + tests + Airflow/Cosmos + Streamlit dashboard | ✅ Done |
| Phase 2 | Semantic layer: 5 governed metrics, defined once, shared by BI and agent | ✅ Done |
| Phase 3 | Agentic copilot: FastAPI + Gemini function-calling + MCP server + NL Q&A | ✅ Done |
| Phase 4 | Deploy: Docker + Terraform + **live on Cloud Run**; screenshots/GIF pending | 🟡 In progress |

---

## Documentation

- [BLUEPRINT.md](BLUEPRINT.md) — full design: architecture, business case, rollout ladder.
- [docs/data-engineering.md](docs/data-engineering.md) — the data-readiness gate (which
  columns the analytics need, and how the dataset satisfies them).
- [docs/mcp.md](docs/mcp.md) — wiring the MCP server into a client (Claude Desktop, Cursor).
- [docs/roadmap.md](docs/roadmap.md) — the incremental checkpoints (the build *story*, not
  just the result).
- [terraform/README.md](terraform/README.md) — the Cloud Run deploy runbook + cost notes.

---

## License

MIT — see [LICENSE](LICENSE).
