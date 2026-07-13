# Data Engineering — First Instance

> Objective first, then the *how*. This doc is the readiness gate for Phase 1: it states
> what the cockpit must produce, how the pipeline produces it, and proves the target
> metrics are buildable from the LendingClub data before any model is written.

## 1. Objective (the *why*)

Produce a small set of **governed metrics** — vintage default curves and cohort
analytics over a consumer-lending book — that power both the BI cockpit and the agentic
copilot. Everything downstream reads these same definitions. If the pipeline can't
produce these metrics honestly from public data, nothing else matters — so this doc
checks that first.

## 2. Where things run — DATA vs COMPUTE

The 1.4 GB CSV never lives on your laptop. Data is always in the cloud; only lightweight
orchestration runs locally.

| Concern | Where it runs | Why |
| :--- | :--- | :--- |
| **Data at rest** | GCS (raw CSV) + BigQuery (raw → marts) | Cloud, always. Never the laptop. |
| **Ingest** (Kaggle → GCS → BQ) | **Cloud Shell VM** (one-time) | Keeps the CSV off your laptop. |
| **dbt transforms** | Your laptop (thin client) | Only *sends SQL*; BigQuery does the compute. |
| **Airflow orchestration** | Your laptop, local Docker (astro) | Coordinates dbt. Local because Cloud Composer ≈ $300/mo. |

Mental model: **laptop = lightweight coordinator + SQL sender; cloud = data + compute.**
Airflow triggers dbt; dbt compiles SQL and hands it to BigQuery; BigQuery builds the
tables. Your machine never holds or crunches the big data.

## 3. The pipeline (the *how*) — layered dbt on BigQuery

```
raw.lending_club_accepted           (autodetect load, as-is)
        │
        ▼  staging  — cast, clean, rename, parse dates
stg_loans
        │
        ▼  intermediate — resolve status, build MOB spine
int_loan_status_resolved   +   date-spine (MOB 1..term)
        │
        ▼  facts
fct_loan            (grain: 1 loan)
fct_loan_month      (grain: loan × month-on-book)   ← generated via date-spine cross join
        │
        ▼  dims: dim_date · dim_borrower · dim_loan_product
        ▼  marts
mart_vintage_curves     mart_cohort_default
```

**Key transforms:**
- `stg_loans`: parse `issue_d` / `last_pymnt_d`, derive `term_months`, standardize
  `loan_status`, keep principal columns for loss metrics.
- `int_loan_status_resolved`: map `loan_status` → `{current, fully_paid, charged_off,
  default}`, derive `default_flag`, approximate charge-off month from `last_pymnt_d`.
- `fct_loan_month`: cross-join each loan against MOB integers `1..term_months` anchored on
  `issue_d`; set `default_flag_at_mob`; flag 2017–2018 originations as **right-censored**.

## 4. Metrics we go fetch — structure + readiness

The semantic-layer metrics and whether this pipeline can build each one from LendingClub
columns. **Readiness:** ✅ direct · ⚠️ buildable with a documented approximation.

| Metric | Definition | Grain / source | Source columns | Ready |
| :--- | :--- | :--- | :--- | :---: |
| `cohort_size` | # loans per issue cohort | `fct_loan` | `issue_d` | ✅ |
| `default_rate` | charged-off loans ÷ cohort size | `fct_loan` | `loan_status` | ✅ |
| `avg_dti` | avg DTI per cohort / grade | `fct_loan` | `dti` | ✅ |
| `cumulative_loss_rate` | cumulative charged-off principal ÷ originated, by MOB | `fct_loan_month` | `loan_amnt`, `total_rec_prncp`, `recoveries` | ⚠️ |
| `charge_off_rate` | charged-off ÷ active, by MOB (valid from `mob_0_12`) | `fct_loan_month` | `loan_status`, `last_pymnt_d` | ⚠️ |

**The two ⚠️ carry the project's documented honesty caveats:**
- Charge-off *month* is approximated from `last_pymnt_d` (the snapshot has no monthly
  payment history) → ±1–3 months noise.
- 2017–2018 originations are right-censored at the snapshot date and labeled as such.

**Verdict:** all five core metrics are buildable from public LendingClub columns. The
engineering in §3 produces exactly what §1 needs — with the approximations owned openly,
not hidden.

## 5. Readiness gate (definition of ready for Phase 1)

Before writing marts, confirm — **right after `make hydrate`** — that the raw table
carries every column the metrics depend on:

```
issue_d · loan_status · last_pymnt_d · loan_amnt · term · grade · sub_grade
· dti · total_rec_prncp · out_prncp · recoveries
```

A one-shot BigQuery `INFORMATION_SCHEMA.COLUMNS` query verifies presence. If any column
is missing or differently named, we adjust `stg_loans` before proceeding. This turns the
"can we even build this?" question into a checkable gate instead of an assumption.
