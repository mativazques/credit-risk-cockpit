# Credit-Risk Cockpit — operational targets.
# Loads .env if present so GCP/Kaggle vars are available to the recipes.
ifneq (,$(wildcard .env))
include .env
export
endif

.DEFAULT_GOAL := help
.PHONY: help hydrate trim teardown

help:
	@echo "hydrate  - ingest Kaggle -> GCS -> BQ, then build dbt marts (full pipeline)"
	@echo "trim     - drop raw GCS object + raw/staging BQ tables, keep marts (zero-storage resting state)"
	@echo "teardown - destroy ALL cloud resources for this project"

# Full pipeline: raw ingestion (+ dbt marts once Phase 1 lands).
hydrate:
	python scripts/ingest.py
	# Phase 1: cd dbt && dbt run && dbt test

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
