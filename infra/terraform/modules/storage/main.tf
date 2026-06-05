# ── Local helpers ─────────────────────────────────────────────────────────────

locals {
  common_labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

# ── Reports Bucket ────────────────────────────────────────────────────────────
# Stores generated settlement / reconciliation reports

resource "google_storage_bucket" "reports" {
  name                        = "${var.project_name}-${var.env}-reports"
  location                    = var.region
  project                     = var.project_id
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = var.nearline_transition_days
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age                = 730
      with_state         = "ARCHIVED"
    }
  }

  labels = local.common_labels
}

# ── Exports Bucket ────────────────────────────────────────────────────────────
# Stores CSV / XLSX data exports requested by users

resource "google_storage_bucket" "exports" {
  name                        = "${var.project_name}-${var.env}-exports"
  location                    = var.region
  project                     = var.project_id
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = var.nearline_transition_days
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365
    }
  }

  labels = local.common_labels
}

# ── Audit Bucket ──────────────────────────────────────────────────────────────
# Immutable audit trail — object retention lock prevents deletion

resource "google_storage_bucket" "audit" {
  name                        = "${var.project_name}-${var.env}-audit"
  location                    = var.region
  project                     = var.project_id
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  retention_policy {
    is_locked        = var.env == "prod"
    retention_period = var.audit_retention_days * 86400
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = var.nearline_transition_days
    }
  }

  labels = local.common_labels
}

# ── IAM Bindings ──────────────────────────────────────────────────────────────

# API SA: read + write to reports and exports
resource "google_storage_bucket_iam_member" "api_reports" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.api_sa_email}"
}

resource "google_storage_bucket_iam_member" "api_exports" {
  bucket = google_storage_bucket.exports.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.api_sa_email}"
}

# Worker SA: full access to all three buckets
resource "google_storage_bucket_iam_member" "worker_reports" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.worker_sa_email}"
}

resource "google_storage_bucket_iam_member" "worker_exports" {
  bucket = google_storage_bucket.exports.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.worker_sa_email}"
}

resource "google_storage_bucket_iam_member" "worker_audit" {
  bucket = google_storage_bucket.audit.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.worker_sa_email}"
}

# Job SA: full access to all three buckets
resource "google_storage_bucket_iam_member" "job_reports" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.job_sa_email}"
}

resource "google_storage_bucket_iam_member" "job_exports" {
  bucket = google_storage_bucket.exports.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.job_sa_email}"
}

resource "google_storage_bucket_iam_member" "job_audit" {
  bucket = google_storage_bucket.audit.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.job_sa_email}"
}
