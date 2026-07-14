variable "project_id" {
  type        = string
  description = "GCP project that hosts the warehouse and the Cloud Run service."
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "Region for Artifact Registry and Cloud Run."
}

variable "image" {
  type        = string
  description = "Full Artifact Registry image URI (with tag) to deploy, e.g. us-central1-docker.pkg.dev/PROJECT/cockpit/credit-risk-cockpit:latest."
}

variable "bq_dbt_dataset" {
  type        = string
  default     = "analytics"
  description = "dbt target dataset; the marts live in <bq_dbt_dataset>_marts."
}

variable "max_instances" {
  type        = number
  default     = 3
  description = "Cloud Run max instances — caps fan-out (and cost) under a traffic spike."
}
