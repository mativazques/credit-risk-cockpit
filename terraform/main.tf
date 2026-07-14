# Credit-Risk Cockpit — deploy/serving infrastructure (C4.2).
#
# Scope: Terraform owns the *serving* layer — the Cloud Run service and everything it
# needs (image registry, runtime identity, IAM, the Gemini secret). The *data* layer
# (the GCS raw bucket and the BigQuery datasets) is intentionally NOT managed here: it
# was bootstrapped by the ingest + dbt pipeline and holds loaded data, so re-declaring it
# under Terraform would risk destroying it. Adopting it into IaC later is a
# `terraform import` away — see terraform/README.md. This split is the honest, safe shape
# for a project that grew a serving layer on top of an already-loaded warehouse.

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- APIs the serving layer needs -------------------------------------------------
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "bigquery.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# --- Container image registry -----------------------------------------------------
resource "google_artifact_registry_repository" "cockpit" {
  location      = var.region
  repository_id = "cockpit"
  format        = "DOCKER"
  description   = "Credit-Risk Cockpit container images"
  depends_on    = [google_project_service.apis]
}

# --- Runtime identity: a dedicated, least-privilege service account ----------------
resource "google_service_account" "run" {
  account_id   = "cockpit-run"
  display_name = "Credit-Risk Cockpit Cloud Run runtime"
}

# Read-only access to the marts. dataViewer (read tables) + jobUser (run queries).
resource "google_project_iam_member" "bq_data_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.run.email}"
}

resource "google_project_iam_member" "bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.run.email}"
}

# --- Gemini API key via Secret Manager --------------------------------------------
# Terraform owns the secret *container* and the runtime's access to it; the secret
# VALUE is added out-of-band (`make secret-push`) so it never lands in tf state or git.
resource "google_secret_manager_secret" "gemini" {
  secret_id = "gemini-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "run_access" {
  secret_id = google_secret_manager_secret.gemini.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run.email}"
}

# --- The public service -----------------------------------------------------------
resource "google_cloud_run_v2_service" "cockpit" {
  name                = "credit-risk-cockpit"
  location            = var.region
  deletion_protection = false

  template {
    service_account = google_service_account.run.email

    # Scale-to-zero: no traffic, no cost. Capped so a traffic spike can't fan out.
    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "BQ_DBT_DATASET"
        value = var.bq_dbt_dataset
      }
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_iam_member.run_access,
  ]
}

# Public, unauthenticated demo — abuse is contained by the copilot's own hardening
# (per-IP + global daily token caps), not by Cloud Run auth.
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.cockpit.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "url" {
  description = "Public URL of the deployed cockpit."
  value       = google_cloud_run_v2_service.cockpit.uri
}
