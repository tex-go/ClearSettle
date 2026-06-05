# ── Terraform State Bucket ────────────────────────────────────────────────────
# Single bucket holds state for all environments.
# Environments are isolated by prefix: dev/, staging/, prod/, global/iam

resource "google_storage_bucket" "tf_state" {
  name                        = var.terraform_state_bucket
  location                    = "ASIA"
  storage_class               = "STANDARD"
  project                     = var.project_id
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age                = 365
      num_newer_versions = 5
      with_state         = "ARCHIVED"
    }
  }

  labels = {
    managed-by = "terraform"
    purpose    = "terraform-state"
  }
}

# ── CI SA: read+write to state bucket ─────────────────────────────────────────

resource "google_storage_bucket_iam_member" "ci_state_rw" {
  bucket = google_storage_bucket.tf_state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.ci_sa_email}"
}

# ── Log Sinks for Audit ───────────────────────────────────────────────────────
# Routes admin activity and data access audit logs to Cloud Logging.
# Individual environment log exclusions are configured per-environment.

resource "google_project_iam_audit_config" "all_services" {
  project = var.project_id
  service = "allServices"

  audit_log_config {
    log_type = "ADMIN_READ"
  }

  audit_log_config {
    log_type = "DATA_WRITE"
  }
}

# ── Log Exclusions ────────────────────────────────────────────────────────────
# Exclude noisy health-check and INFO logs to reduce logging costs.

resource "google_logging_project_exclusion" "health_checks" {
  name        = "exclude-health-checks"
  project     = var.project_id
  description = "Drop noisy Cloud Run health check 200 responses"
  filter      = "resource.type=\"cloud_run_revision\" httpRequest.requestUrl:\"/health\" httpRequest.status=200"
}

resource "google_logging_project_exclusion" "cloudrun_debug" {
  name        = "exclude-cloudrun-debug"
  project     = var.project_id
  description = "Drop verbose DEBUG-level Cloud Run logs in prod"
  filter      = "resource.type=\"cloud_run_revision\" severity=DEBUG"
}

# ── Log Retention ─────────────────────────────────────────────────────────────
# Default retention is 30 days. _Required bucket is non-configurable.
# Override _Default to retain errors + warnings for 365 days.

resource "google_logging_project_bucket_config" "default" {
  project        = var.project_id
  location       = "global"
  retention_days = 365
  bucket_id      = "_Default"
}
