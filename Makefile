# Credit-Risk Cockpit — operational targets.
# Loads .env if present so GCP/Kaggle vars are available to the recipes.
ifneq (,$(wildcard .env))
include .env
export
endif

# Interpreter: defaults to python3; override to use a venv, e.g. `make hydrate PYTHON=.venv/bin/python`.
PYTHON ?= python3
DBT ?= .venv/bin/dbt
DBT_DIR := dbt
# The Streamlit app has its own venv: streamlit pins protobuf<6 while dbt needs >=6,
# so they cannot share an environment. Create it with:
#   python3 -m venv .venv-app && .venv-app/bin/pip install -r app/requirements.txt
APP_PYTHON ?= .venv-app/bin/python
# dbt reads GCP_PROJECT / BQ_DBT_DATASET / BQ_LOCATION from the exported .env above.
export DBT_PROFILES_DIR := $(abspath dbt)

.DEFAULT_GOAL := help
.PHONY: help hydrate app trim teardown dbt-debug dbt-run dbt-test dbt-build dbt-docs

help:
	@echo "hydrate   - ingest Kaggle -> GCS -> BQ, then build + test dbt models (full pipeline)"
	@echo "dbt-debug - check dbt connects to BigQuery"
	@echo "dbt-run   - build dbt models        (SELECT=name to target one, e.g. SELECT=stg_loans)"
	@echo "dbt-test  - run dbt data tests       (SELECT=... optional)"
	@echo "dbt-build - run + test in DAG order  (SELECT=... optional)"
	@echo "dbt-docs  - generate dbt docs"
	@echo "app       - run the Streamlit cockpit locally (reads the marts)"
	@echo "trim      - drop raw GCS object + raw BQ table, keep marts (zero-storage resting state)"
	@echo "teardown  - destroy ALL cloud resources for this project"

# Full pipeline: raw ingestion, then build + test the dbt DAG.
hydrate:
	$(PYTHON) scripts/ingest.py
	$(DBT) build --project-dir $(DBT_DIR)

dbt-debug:
	$(DBT) debug --project-dir $(DBT_DIR)

dbt-run:
	$(DBT) run --project-dir $(DBT_DIR) $(if $(SELECT),-s $(SELECT),)

dbt-test:
	$(DBT) test --project-dir $(DBT_DIR) $(if $(SELECT),-s $(SELECT),)

dbt-build:
	$(DBT) build --project-dir $(DBT_DIR) $(if $(SELECT),-s $(SELECT),)

dbt-docs:
	$(DBT) docs generate --project-dir $(DBT_DIR)

# Local BI cockpit. Reads the marts via ADC; wrap queries in @st.cache_data.
app:
	$(APP_PYTHON) -m streamlit run app/main.py

# Ephemeral raw: keep the thin serving marts, drop the heavy raw layer.
# Re-hydrate anytime with `make hydrate`.
trim:
	@echo "Trimming raw layer (marts are kept)..."
	-gsutil -m rm -r gs://$(GCS_BUCKET)/lending_club/ 2>/dev/null || true
	-bq rm -f -t $(GCP_PROJECT):$(BQ_DATASET).$(BQ_RAW_TABLE)
	# Phase 1: also drop the dbt staging tables/dataset here once they exist.
	@echo "Done. Re-hydrate anytime with: make hydrate"

# Full destroy. Terraform owns the project in Phase 4; the gsutil/bq lines are a
# fallback so teardown works before Terraform exists.
teardown:
	@echo "Destroying all cloud resources..."
	# Phase 4: cd terraform && terraform destroy -auto-approve
	-gsutil -m rm -r gs://$(GCS_BUCKET) 2>/dev/null || true
	-bq rm -r -f -d $(GCP_PROJECT):$(BQ_DATASET)
	@echo "Teardown complete."
