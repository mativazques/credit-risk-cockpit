# Credit-Risk Cockpit

A credit-risk and affordability cockpit for a consumer-lending book: vintage default
curves and cohort heatmaps in BI, plus an agentic copilot that answers risk questions in
natural language over a governed dbt semantic layer.

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

[PLACEHOLDER — Phase 1: Streamlit dashboard with vintage curves and cohort heatmap]

[PLACEHOLDER — Phase 3: GIF of copilot answering a cohort question end-to-end]

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

---

## Stack

Python · SQL · BigQuery · dbt · Airflow (Cosmos) · FastAPI · Gemini (Vertex AI) · MCP · Streamlit · Cloud Run · GCP · Terraform

---

## How to Run

[PLACEHOLDER — Phase 0/1: prerequisites (.env.example, GCP project, Kaggle account),
ingestion (`python scripts/ingest.py`), dbt run (`dbt run && dbt test`), Airflow
(`astro dev start`), Streamlit (`streamlit run app/cockpit.py`).]

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
| Phase 0 | Scaffold: repo, .gitignore, ingestion, initial README | In progress |
| Phase 1 | BI core: dbt models + tests + Airflow/Cosmos + Streamlit dashboard | Planned |
| Phase 2 | Semantic layer: metrics defined once, shared by BI and agent | Planned |
| Phase 3 | Agentic copilot: FastAPI + Gemini + MCP tools + NL Q&A | Planned |
| Phase 4 | Polish and deploy: Cloud Run, Terraform, teardown script, GIF demo | Planned |

---

## License

MIT — see [LICENSE](LICENSE).
