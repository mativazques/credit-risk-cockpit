"""Credit-Risk Cockpit — batch pipeline (C1.7).

    ingest (Kaggle -> GCS -> BigQuery)  ->  dbt run + dbt test  (via Cosmos)

Cosmos renders EACH dbt model as its own Airflow task (with its tests right after),
so the DAG mirrors the dbt lineage instead of hiding it behind a single
`BashOperator dbt run`. The dbt project and the ingest script are bind-mounted from
the repo (see docker-compose.override.yml) — one source of truth, no duplication.

Honest framing: on the static LendingClub snapshot this batch runs once. It is written
for incremental ingestion (schedule it @daily in production) and included as a
production-readiness demonstration.

Run it locally: `cd airflow && astro dev start` (needs Docker + the Astro CLI), then
trigger `credit_risk_pipeline` from the Airflow UI at http://localhost:8080.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from cosmos import DbtTaskGroup, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import TestBehavior

# Paths inside the Airflow containers (bind-mounted from the repo).
DBT_PROJECT_DIR = Path("/usr/local/airflow/dbt")
INGEST_SCRIPT = "/usr/local/airflow/scripts/ingest.py"

# Reuse the dbt project's own env-driven profiles.yml (oauth/ADC), same as running
# dbt locally. The container gets ADC via the mounted ~/.config/gcloud and the
# GCP_* env vars from the repo .env (both wired in docker-compose.override.yml).
profile_config = ProfileConfig(
    profile_name="credit_risk_cockpit",
    target_name="dev",
    profiles_yml_filepath=DBT_PROJECT_DIR / "profiles.yml",
)

project_config = ProjectConfig(dbt_project_path=DBT_PROJECT_DIR)

# One task per model, each followed by its data tests -> the classic
# "dbt run then dbt test" gate, but per-model with real lineage.
render_config = RenderConfig(test_behavior=TestBehavior.AFTER_EACH)

with DAG(
    dag_id="credit_risk_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule=None,  # @daily in production; static dataset runs on demand here
    catchup=False,
    tags=["credit-risk", "dbt", "bigquery"],
) as dag:

    ingest = BashOperator(
        task_id="ingest",
        bash_command=f"python {INGEST_SCRIPT}",
    )

    transform = DbtTaskGroup(
        group_id="dbt",
        project_config=project_config,
        profile_config=profile_config,
        render_config=render_config,
    )

    ingest >> transform
