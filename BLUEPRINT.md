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
  the cockpit chips at. Scale is illustrative and linear — substitute any book size; the
  arithmetic is identical.
- Amplifier (qualitative, not quantified): DORA + governance raise the cost of
  inconsistent, non-auditable metrics. Not credited as € benefit — attributing avoided
  fines to a BI tool is not defensible.

### Hard benefit — loss avoidance (the core)
Benefit = influenced book × Δ loss-rate avoided.

**Influenced share — pilot-then-scale ladder (not a claimed fixed %).**
The true influenced share depends on deployment breadth; rather than assume a fixed
percentage of the full €2B book, the model uses a pilot anchor that grows via a rollout
ladder. The cockpit is first deployed on ONE actively-managed portfolio/product line;
illustrative pilot size ≈ **€200M receivables** (one product line / a few origination
vintages under active review).

**Rollout ladder × detection-lift sensitivity (base Δ = 5 bp):**

| Deployment stage | Influenced book | Annual hard benefit (5 bp base) |
| :--- | :--- | :--- |
| Pilot (1 product line) | **€200M** | **€100k/yr** |
| Partial rollout (3 product lines) | **€600M** | **€300k/yr** |
| Full managed book | **€1.2B** | **€600k/yr** |

*(Unit: 1 bp = €100k per €1B receivables. Benefit = influenced book × Δ bp.)*

**Detection-lift sensitivity (second axis — each stage has a low/base/high):**

| Δ loss avoided | Pilot €200M | Partial €600M | Full €1.2B |
| :--- | :--- | :--- | :--- |
| Conservative 2 bp | **€40k** | **€120k** | **€240k** |
| Base 5 bp | **€100k** | **€300k** | **€600k** |
| Best 10 bp | **€200k** | **€600k** | **€1.2M** |

*Ceiling context only (NOT the claim):* McKinsey attributes 20–40% credit-loss
reduction to next-gen decisioning *models* — our tool is monitoring, not a model, so we
sit far below that. Vendor early-warning claims (3–5 mo earlier detection, 10–20% lower
provisions) are unaudited — used to motivate the mechanism, not to size the benefit.

### Soft benefit — analyst time (presented separately, does NOT carry the ROI)
- ~45% of analyst time goes to data prep/ad-hoc (Anaconda survey). Redeploy a
  conservative slice via self-service NL Q&A.
- *Illustrative:* 3 risk analysts × €90k loaded × ~15–25% time redeployed ≈ **€40–70k/yr**.

### Costs / TCO (year 1)
- **Build:** one mid-senior engineer ~3–4 months → **€70–100k**.
- **Run** (production estimate for a live book):
  - BigQuery on-demand: **~€2–4k/yr**
  - Cloud Run: **~€1–2k/yr**
  - Vertex AI inference (Gemini Flash, narrow tool-call payloads): **~€5–12k/yr**
  - Total run: **~€8–18k/yr**
- **Change management:** ~€5–10k.
- **Year-1 TCO ≈ €85–130k.**
- *(This is the production estimate for a live book; the PORTFOLIO DEMO itself runs at
  ~$0/mo on GCP free tier — see Cost controls.)*

### ROI & payback
- **Pilot base case (5 bp, €200M):** €100k hard + €50k soft = €150k vs ~€110k TCO →
  **payback ≈ 9 months**, Year-1 ROI ~1.4×.
- **Partial rollout base case:** €300k hard + €50k soft = €350k vs ~€110k TCO →
  **payback ≈ 4–5 months**, Year-1 ROI ~2–3×.
- **Worst-case pilot (2 bp, €200M, soft zeroed):** €40k hard vs ~€0 run cost for demo
  (portfolio demo runs at $0/mo) → still positive from year 2 on run cost alone. The
  case survives its worst assumptions at every scale — that's the point.

### Key assumptions & risks (own them)
- Assumptions: book €2B, loss 4%, pilot €200M, rollout ladder to €1.2B, Δ 2–10 bp,
  redeploy 15–25%. Influenced share is modeled as a pilot-then-scale ladder, not a
  claimed fixed %, because the true share depends on deployment breadth. **The Δ-bp
  and adoption are the sensitive levers** — everything else is arithmetic or benchmark.
- Risks: *attribution* (did the tool cause the avoided loss, or the analyst?) and
  *adoption* (risk managers must actually use the copilot). Mitigation: pilot on one
  portfolio, measure detection-lead-time before/after, risk-adjust benefits TEI-style.
- Public portfolio — no real book. All numbers illustrative with stated assumptions.

## What BI does vs what the agent does
- **BI (standing views):** vintage curves (months-on-book vs cumulative default),
  cohort heatmaps, DTI / grade distributions, portfolio KPIs. (Roll-rate tables deferred
  to backlog — see Dimensional model section.)
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
                          → Streamlit  (BI cockpit + chat)
                          → FastAPI + Gemini (Vertex AI) + MCP  (agentic copilot)
                          → Cloud Run (deploy, min-instances=0)   ·   Terraform (IaC)
```

### Orchestration (Airflow + Cosmos)
- Airflow runs the batch: `ingest (CSV→GCS→BQ)` → `dbt run` → `dbt test`.
- **Run Airflow locally via Docker** (Astronomer `astro` CLI / docker-compose). **NOT
  Cloud Composer** — managed Airflow costs ~USD 300–400+/mo, unjustifiable for a solo
  portfolio. Local shows the same skill: the DAG and code are what matter.
- **Integrate dbt with `astronomer-cosmos`**, not a black-box `BashOperator dbt run`.
  Cosmos renders **each dbt model as its own Airflow task** with real dependencies →
  the DAG mirrors the lineage; this is the modern pattern NL/DE data teams expect.
- Honest framing: on a static Kaggle dataset the batch runs once, but the DAG is written
  for incremental ingestion — included as a *production-readiness demonstration*, reusing
  existing Airflow experience.

### Dimensional model (dbt on BigQuery)
- **Facts:** `fct_loan` (grain: loan), `fct_loan_month` (grain: loan × month-on-book,
  for vintage curves).
- **Dims:** `dim_borrower`, `dim_date`, `dim_loan_product` (grade, sub_grade,
  term_months, int_rate_band).
- **Marts:** `mart_vintage_curves`, `mart_cohort_default`.
- **Semantic layer:** metrics — `default_rate`, `cumulative_loss_rate`, `cohort_size`,
  `avg_dti`, `charge_off_rate` — defined once, consumed by BI and agent.
- dbt tests + docs on every model (shows analytics-eng rigor).

**Grain construction for `fct_loan_month`:** LendingClub is a loan-level SNAPSHOT, not
a monthly payment history. `fct_loan_month` is GENERATED via a dbt date-spine —
cross-join each loan against MOB integers 1..term anchored on `issue_d`. The
`default_flag` at each MOB is derived from `loan_status` + `last_pymnt_d` (charge-off
month approximated as `last_pymnt_d` for defaulted loans, ±1–3 months noise). 2017–2018
originations are right-censored at the snapshot date and must be labeled as such. This
is a standard, interview-defensible approach for public snapshot data.

**Backlog / deferred — roll rates:** `mart_roll_rates` requires per-month loan status
transitions, which the LendingClub snapshot does not carry (only final `loan_status`).
Deferred to a later phase; buildable via a synthetic state-machine and clearly labeled
"simulated" if pursued.

### Agentic copilot
- **FastAPI** service, **`gemini-3.5-flash` via Vertex AI** (per stack default; Claude
  deferred). Model choice + spend bounding covered in Cost & abuse hardening.
- **MCP server** exposing governed tools: `list_metrics`, `query_metric(cohort, window)`,
  `compare_cohorts(a, b, metric)`. Agent decomposes the question → calls tools →
  narrates. No free-form SQL against raw tables.
- **`window` enum contract for `query_metric`:** allowed values `mob_0_6`, `mob_0_12`,
  `mob_0_24`, `mob_0_36`, `mob_0_60`, `lifetime`. Each metric declares which windows are
  valid (e.g. `cumulative_loss_rate` is valid for all; `charge_off_rate` is valid from
  `mob_0_12` onward). Requests for an invalid window return a structured error, not SQL.
- Front-end: Streamlit (cockpit + chat in one app on Cloud Run).

### Cost controls
Goal: absolute **$0/mo** for the portfolio demo on GCP free tier.

- **BigQuery:** all Streamlit queries wrapped in `@st.cache_data(ttl=3600)` — static
  dataset, no freshness loss; avoids repeated on-demand scan charges.
- **Cloud Run:** `min-instances=0` (scale-to-zero); cold start ~4 s is acceptable for a
  portfolio demo.
- **Vertex AI:** model pinned to `gemini-3.5-flash` (GA, no announced retirement; the
  `2.0-flash` family was shut down 2026-06-01 and `2.5-flash` retires 2026-10-16). Pricing
  ~$1.50/M input · $9.00/M output · $0.15/M cached input. Tool-call payloads kept narrow
  (metric names + filters only, not raw table dumps); `max_output_tokens` capped and the
  fixed system prompt + metric catalog served via context caching. See Cost & abuse
  hardening for how public LLM spend is bounded against abuse.
- **GCS:** single bucket, ~1.4 GB raw CSV within the 5 GB free-tier allowance.
- **Artifact Registry:** lean container image (<0.5 GB) stays within the free tier.
- **Raw CSV never committed** to the repo (requires a free Kaggle account to download).
- **Ephemeral raw layer (`make trim`).** The raw CSV/table is reproducible from Kaggle,
  so it is treated as disposable, not precious. The serving layer (Streamlit) reads only
  the small pre-aggregated marts (KB–MB), never the ~1.4 GB raw. `make trim` drops the
  raw GCS object + `raw`/`staging` BQ tables and keeps the marts, so the demo's resting
  state is ~$0 storage. Since the GCS 5 GB / BQ 10 GB Always-Free tiers are
  **billing-account-wide** (shared across projects), trimming finished flagships frees
  headroom for new portfolio projects. Re-hydrate anytime with `make hydrate` (ingest +
  dbt run). Honest tradeoff: while trimmed the pipeline can't `dbt run` until re-ingested
  — fine for a demo on static data; the DAG/Terraform still demonstrate the full pipeline.
- **Tear-down requirement:** a `make teardown` (Terraform's `terraform destroy`) that
  destroys the Cloud Run service, GCS bucket, and BigQuery dataset must exist before
  Phase 4 is marked done. `trim` keeps the thin serving layer alive; `teardown` nukes
  everything.

### Cost & abuse hardening (public LLM demo)
A public copilot URL is an anonymous, per-message token-spend endpoint — an abuse vector.
Two facts drive the design: (1) **GCP budgets do not cap spend, they only alert** — the
only hard cap is a kill-switch that disables billing; (2) **`gemini-3.5-flash` uses
Dynamic Shared Quota**, so the cap cannot come from a Vertex RPM quota knob — it must come
from the app layer + the kill-switch. Strategy: **bound `cost-per-call × call-count`, then
a billing kill-switch as backstop** → spend is mathematically bounded.

**Worst-case math (reassurance):** per call bounded to input ≤1k tokens (~$0.0015) +
`max_output_tokens=512` (~$0.0046) ≈ **~$0.006/call**. A global daily cap of 500 calls →
**~$3/day** worst case; a billing kill-switch at a low budget makes bankruptcy impossible.

Defense in depth (most effective first):
- **L0 — Product decision.** The live copilot is **public and fully usable by anyone** —
  the point is a working product, not a mock. What makes that safe is L1–L5: the global
  daily cap is the abuse ceiling (once hit, later visitors that day get a graceful "demo
  limit reached"), and the kill-switch bounds the month. The **recorded GIF in the README
  is the preview, not a substitute** — it lets someone see it work instantly (no cold
  start, zero token spend to *view*) before they click through to the live app.
- **L1 — Bound per-call cost.** `gemini-3.5-flash`, `max_output_tokens=512`, reject input
  over N chars *before* calling Gemini, context-cache the system prompt + metric catalog.
- **L2 — Bound call volume.** Per-IP + per-session rate limit (token bucket in FastAPI);
  a global daily cap (counter) that returns a canned "demo limit reached" without hitting
  Gemini; Cloud Run `max-instances` + `concurrency` cap parallelism.
- **L3 — On-topic router.** A cheap deterministic pre-filter (allowed intents/keywords or
  embedding similarity) runs BEFORE the expensive call; off-topic questions get a canned
  refusal with **zero Gemini tokens** ("I only answer questions about this demo's
  credit-risk metrics — vintage, cohorts, default rate…"). Reinforced by the existing
  tool-constrained design: the model can only call `list_metrics`/`query_metric`/
  `compare_cohorts`, so off-topic maps to no tool → cheap structured refusal.
- **L4 — Cache.** Exact/semantic cache of `question → answer` kills repeated-spam cost.
- **L5 — Backstop (the only hard cap).** Budget → Pub/Sub → Cloud Function that disables
  billing on the project, plus budget alerts at 50/90/100%. Delivered via Terraform.

## Phased plan
- **Phase 0 — Scaffold.** Repo, `.gitignore` (secrets out), ingestion script CSV→GCS→BQ,
  initial README. Git identity = matirvazques@gmail.com.

  **Kickoff checklist (start the next coding session here):**
  1. **Data source — LendingClub (Kaggle, CC0).** Dataset `wordsforthewise/lending-club`,
     file `accepted_2007_to_2018Q4.csv` (~2.26M loans, ~1.4 GB). Not committed — pulled at
     runtime. As of 2026-07-13 the file is **NOT yet downloaded**; the Kaggle CLI and creds
     are **not yet installed** on this machine.
  2. **Kaggle CLI setup.** `pip install kaggle`. Get an API token at
     kaggle.com → Account → *Create New Token* (downloads `kaggle.json`). Provide it as
     `KAGGLE_USERNAME` / `KAGGLE_KEY` in a git-ignored `.env` (do NOT commit `kaggle.json`).
     Verify with `kaggle datasets list`.
  3. **GCP project.** Confirm the active project on `matirvazques@gmail.com`
     (`gcloud config get-value project`). Enable BigQuery + Cloud Storage APIs. One GCS
     bucket (raw) + one BigQuery dataset (raw). Stay in free tier — see Cost controls.
  4. **Ingestion script** `scripts/ingest.py`: Kaggle download → upload CSV to GCS →
     load into BigQuery `raw` dataset (schema autodetect or explicit).
  5. **Folder scaffold:** `dbt/` (project + profiles via env, not committed),
     `airflow/` (Astro project, Cosmos), `scripts/`, `app/` (Streamlit later), `.env.example`.
  6. **Secrets hygiene:** confirm `.env`, `kaggle.json`, `*.json` service-account keys,
     and `dbt profiles` are all in `.gitignore` BEFORE the first data-related commit.
- **Phase 1 — BI core (standalone win).** Airflow with astronomer-cosmos set up from the
  start (each dbt model as its own Airflow task, real lineage in the DAG). dbt: staging +
  vintage/cohort marts + tests + docs. Dashboard with vintage curves + cohort heatmap.
  *This alone is a strong analytics-eng portfolio piece.*
- **Phase 2 — Semantic layer.** Metrics defined once; BI and agent read the same defs.
- **Phase 3 — Agentic copilot.** FastAPI + `gemini-3.5-flash` (Vertex AI) + MCP tools over
  the semantic layer; NL risk Q&A with narrative diagnosis. *This is the differentiator.*
  Includes the **app-layer cost/abuse hardening** (L1–L4 in Cost & abuse hardening):
  on-topic router, input caps + `max_output_tokens`, per-IP + global rate limit, cache.
- **Phase 4 — Polish & deploy.** Cloud Run deploy (`min-instances=0`), Terraform (main.tf
  covering GCS bucket + BigQuery dataset + Cloud Run service + Artifact Registry repo +
  IAM bindings, **plus the billing kill-switch: budget + Pub/Sub + billing-disable Cloud
  Function, and Cloud Run `max-instances`** — L5 of the hardening), a **public, live,
  fully-usable copilot** protected by the daily cap + kill-switch (L0; GIF is the README
  preview, not a gate),
  `make hydrate`/`trim`/`teardown` targets (trim keeps marts, teardown destroys all via
  `terraform destroy`), README with screenshots/GIF + a short write-up.

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
4. **`mart_roll_rates` deferred to backlog** — the LendingClub snapshot carries only
   final `loan_status`, not per-month transitions. Roll rates are buildable via a
   synthetic state-machine (labeled "simulated") in a later phase.
5. **Terraform IS included in v1** — `main.tf` covering 4–5 resources (GCS bucket,
   BigQuery dataset, Cloud Run service, Artifact Registry repo, IAM bindings), delivered
   in Phase 4. Not optional.
6. **Infrastructure goal: absolute $0/mo for the portfolio demo** — achieved via
   scale-to-zero Cloud Run, BigQuery caching, GCS/Artifact Registry within free tiers,
   and Gemini Flash with narrow payloads. See Cost controls.
7. **License: MIT.**

## Status
- Design/blueprint: **done.**
- Next up: **Phase 0 scaffold** (folder structure, `.gitignore`, initial dbt project,
  Airflow DAG, CSV→GCS→BQ ingestion script). No code written yet.
