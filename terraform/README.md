# Deploy — Terraform + Cloud Run (C4.2)

Terraform owns the **serving layer**: the Cloud Run service and everything it needs
(Artifact Registry, a least-privilege runtime service account, IAM, the Gemini secret).
The **data layer** (GCS raw bucket + BigQuery datasets) is left as bootstrapped by the
ingest/dbt pipeline — see the note at the top of [`main.tf`](main.tf).

## One-time / per-deploy runbook

All targets read `GCP_PROJECT`, `GCP_REGION`, `BQ_DBT_DATASET`, and `GEMINI_API_KEY`
from `.env`. Run from the repo root.

```bash
make tf-init         # terraform init

# 1. Create the registry + secret container + enable APIs (needed before we can push).
make tf-bootstrap

# 2. Push the Gemini key into Secret Manager (value never touches git or tf state).
make secret-push

# 3. Build the image for Cloud Run (linux/amd64) and push it to Artifact Registry.
make image-push

# 4. Create/patch the Cloud Run service and wire the image. Prints the public URL.
make deploy
```

Re-deploying after a code change is just `make image-push && make deploy`.

## What it costs

- **Cloud Run**: `min_instance_count = 0` → scale-to-zero. Idle cost is **$0**; you pay
  only for request-time CPU/memory. `max_instances` caps fan-out.
- **Artifact Registry**: the image is ~1.3 GB; the free tier is 0.5 GB, so storage is a
  few cents/month. Prune old tags to stay near-free.
- **Secret Manager**: one active secret, effectively free.
- **BigQuery**: on-demand query bytes, cached 1h by the app; the marts are tiny.

The copilot's own hardening (per-IP + global daily token caps) keeps the public,
unauthenticated endpoint within the Gemini free tier.

## Tear down

`make teardown` runs `terraform destroy` (removes the Cloud Run service, SA, IAM,
registry, and secret) and leaves the data layer intact. `make trim` separately drops the
heavy raw layer while keeping the marts.
