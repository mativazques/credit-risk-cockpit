# Credit-Risk Cockpit — Blueprint

> Flagship #1. A credit-risk & affordability cockpit for a consumer-lending book:
> cohort/vintage default analytics in BI, plus an **agentic copilot** that answers
> risk questions in natural language over a governed dbt semantic layer.

## Why this project
Sits dead-center on Matias's defensible domain (cohorts, vintage curves, consumer
credit) and showcases the differentiator (production agentic AI on a modern data
stack). Rides urgent 2025–26 NL/DE fintech pains: lending affordability under open
banking + credit exposure under PSD3.

## The pitch (one line)
"A risk manager opens the cockpit to see vintage default curves and cohort heatmaps —
then asks *'why did the Q3-2021 cohort's default rate lift vs Q2?'* and the copilot
queries the same governed metrics, compares cohorts, and narrates the driver."

## Business case (the *why* — this drives everything; the stack serves it)

> Framing: **loss-avoidance as insurance**, not a promised fixed % cut. The cockpit
> shortens the tail and speeds detection; even a few bp of avoided loss on the part of
> the book it influences pays for it. Every number below is an **illustrative,
> conservative model with stated assumptions** (public portfolio — no real book).
> Benefits are split **hard** (loss avoidance, defensible arithmetic) vs **soft**
> (analyst time, governance) so the ROI survives even if soft benefits are zeroed.

### Cost of inaction (baseline)
- EU consumer-credit loss rates run **~3–6%/yr** (EBA consumer-credit NPL ≈ 5.4% Jun-2025;
  US card net charge-off ≈ 4% as a flow cross-check). Anchor: **4%**.
- The clean, defensible unit: **1 bp of loss = €100k/yr per €1B of receivables**
  (€1B × 0.0001). So a 4% book loses **~€40M/yr per €1B**.
- *Illustrative book:* **€2B receivables → ~€80M/yr in credit losses.** That is the pool
  the cockpit chips at.
- Amplifier (qualitative, not quantified): DORA + governance raise the cost of
  inconsistent, non-auditable metrics. Not credited as € benefit — attributing avoided
  fines to a BI tool is not defensible.

### Hard benefit — loss avoidance (the core)
Benefit = influenced book × Δ loss-rate avoided. Explicit multipliers:
- **Influenced share:** cockpit only sways decisions on actively-managed cohorts / new
  originations → assume **30%** of €2B = **€600M**.
- **Δ loss avoided** via earlier cohort/vintage detection — modeled as an assumption,
  sensitivity-tested:

| Case | Δ loss on influenced book | Annual hard benefit |
| :--- | :--- | :--- |
| Conservative | 2 bp | **€120k** |
| Base | 5 bp | **€300k** |
| Best | 10 bp | **€600k** |

*Ceiling context only (NOT the claim):* McKinsey attributes 20–40% credit-loss
reduction to next-gen decisioning *models* — our tool is monitoring, not a model, so we
sit far below that. Vendor early-warning claims (3–5 mo earlier detection, 10–20% lower
provisions) are unaudited — used to motivate the mechanism, not to size the benefit.

### Soft benefit — analyst time (presented separately, does NOT carry the ROI)
- ~45% of analyst time goes to data prep/ad-hoc (Anaconda survey). Redeploy a
  conservative slice via self-service NL Q&A.
- *Illustrative:* 3 risk analysts × €90k loaded × ~15–25% time redeployed ≈ **€40–70k/yr**.

### Costs / TCO (year 1)
- Build (one engineer, a few months) **€60–100k** + run (BigQuery, dbt, Cloud Run, LLM
  inference) **~€10–20k/yr** + change management. **Year-1 TCO ≈ €80–130k.**

### ROI & payback
- **Base case:** €300k hard + €50k soft = €350k vs ~€110k TCO → **payback ≈ 4–5 months**,
  Year-1 ROI ~2–3×.
- **Conservative case (hard only, soft zeroed):** €120k vs €110k → **≈ break-even in
  year 1**, clearly positive from year 2 (run cost only). The case survives its own
  worst assumptions — that's the point.

### Key assumptions & risks (own them)
- Assumptions: book €2B, loss 4%, influenced 30%, Δ 2–10 bp, redeploy 15–25%. **The
  Δ-bp and adoption are the sensitive levers** — everything else is arithmetic or benchmark.
- Risks: *attribution* (did the tool cause the avoided loss, or the analyst?) and
  *adoption* (risk managers must actually use the copiloto). Mitigation: pilot on one
  portfolio, measure detection-lead-time before/after, risk-adjust benefits TEI-style.

## What BI does vs what the agent does
- **BI (standing views):** vintage curves (months-on-book vs cumulative default),
  cohort heatmaps, roll-rate tables, DTI / grade distributions, portfolio KPIs.
- **Agent (ad-hoc "why"):** natural-language questions, cross-cohort comparisons,
  narrative diagnosis, anomaly explanation. Only where NL Q&A genuinely beats clicking.
- **Non-gratuitous rule:** the agent does **text-to-metric** over the semantic layer
  (safe, governed), NOT raw text-to-SQL. Same metric definitions power BI and agent.

## Data (public)
- **Primary — LendingClub loan data** (Kaggle, ~2M loans). Has origination date, grade,
  term, DTI, and loan status over time → perfect for **vintage/cohort** default curves.
- **Optional — Home Credit Default Risk** (Kaggle): application + bureau + installment
  data → feeds an **affordability** score if we extend.
- Honest footer in README: public/sample datasets, no proprietary data.

## Architecture (GCP)
```
                    ┌──────────── Airflow (orchestration) ────────────┐
                    │  ingest → dbt run → dbt test  (via Cosmos)       │
                    └──────────────────────┬──────────────────────────┘
                                           ▼
Kaggle CSV → GCS (raw) → BigQuery (raw)
                          → dbt (staging → intermediate → marts + semantic layer)
                          → Looker Studio / Streamlit  (BI cockpit)
                          → FastAPI + Gemini (Vertex AI) + MCP  (agentic copilot)
                          → Cloud Run (deploy)   ·   Terraform (IaC, later)
```

### Orchestration (Airflow + Cosmos)
- Airflow runs the batch: `ingest (CSV→GCS→BQ)` → `dbt run` → `dbt test`.
- **Run Airflow locally via Docker** (Astronomer `astro` CLI / docker-compose). **NOT
  Cloud Composer** — managed Airflow costs ~USD 300–400+/mo, unjustifiable for a solo
  portfolio. Local shows the same skill: the DAG and code are what matter.
- **Integrate dbt with `astronomer-cosmos`**, not a black-box `BashOperator dbt run`.
  Cosmos renders **each dbt model as its own Airflow task** with real dependencies →
  the DAG mirrors the lineage; this is the modern pattern NL/DE data teams expect.
- Honest framing: on a static Kaggle dataset orchestration is somewhat "gratuitous"
  (runs once) — included as a *skill demonstration*, reusing existing Airflow chops.

### Dimensional model (dbt on BigQuery)
- **Facts:** `fct_loan` (grain: loan), `fct_loan_month` (grain: loan × month-on-book,
  for vintage curves).
- **Dims:** `dim_borrower`, `dim_date`, `dim_grade` (product/grade/term).
- **Marts:** `mart_vintage_curves`, `mart_cohort_default`, `mart_roll_rates`.
- **Semantic layer:** metrics — `default_rate`, `cumulative_loss_rate`, `cohort_size`,
  `avg_dti`, `charge_off_rate` — defined once, consumed by BI and agent.
- dbt tests + docs on every model (shows analytics-eng rigor).

### Agentic copilot
- **FastAPI** service, **Gemini via Vertex AI** (per stack default; Claude deferred).
- **MCP server** exposing governed tools: `list_metrics`, `query_metric(cohort, window)`,
  `compare_cohorts(a, b, metric)`. Agent decomposes the question → calls tools →
  narrates. No free-form SQL against raw tables.
- Front-end: Streamlit (cockpit + chat in one) OR Looker Studio for BI + a chat widget.

## Phased plan
- **Phase 0 — Scaffold.** Repo, `.gitignore` (secrets out), ingestion script CSV→GCS→BQ,
  initial README. Git identity = matirvazques@gmail.com.
- **Phase 1 — BI core (standalone win).** dbt: staging + vintage/cohort marts + tests +
  docs. Dashboard with vintage curves + cohort heatmap. Simple Airflow DAG
  (`ingest → dbt run → dbt test`, BashOperator first). *This alone is a strong
  analytics-eng portfolio piece.*
- **Phase 2 — Semantic layer.** Metrics defined once; BI and agent read the same defs.
- **Phase 3 — Agentic copilot.** FastAPI + Gemini + MCP tools over the semantic layer;
  NL risk Q&A with narrative diagnosis. *This is the differentiator.*
- **Phase 4 — Polish & deploy.** Upgrade the Airflow DAG to Cosmos (model-level tasks),
  Cloud Run deploy, optional Terraform, README with screenshots/GIF + a short write-up.

## Interview story (defensibility)
Every layer maps to something Matias owns day-to-day: cohorts, vintage curves, credit
risk, business planning. The agent isn't a toy — it answers the exact "why did this
cohort move?" questions a risk/planning team asks. Public data, honestly labeled.

## Decisions (RESOLVED — do not re-ask)
1. **BI tool: Streamlit on Cloud Run** — hosts the BI cockpit + the copilot in one app,
   shows more engineering. (Looker Studio rejected.)
2. **Scope of v1: LendingClub-only** — vintage/cohort analytics first. Home Credit
   affordability is a later extension, NOT in v1.
3. **Public repo name: `credit-risk-cockpit`.**

## Status
- Design/blueprint: **done.**
- Next up: **Phase 0 scaffold** (folder structure, `.gitignore`, initial dbt project,
  Airflow DAG, CSV→GCS→BQ ingestion script). No code written yet.
