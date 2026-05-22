resource "google_storage_bucket" "uploads" {
  name                        = "${var.project_name}-${var.env}-uploads"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = var.env != "prod"

  versioning { enabled = var.env == "prod" }

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 365 }
  }

  cors {
    origin          = ["https://${var.domain}"]
    method          = ["GET", "PUT", "POST"]
    response_header = ["Content-Type", "Authorization"]
    max_age_seconds = 3600
  }

  labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

resource "google_storage_bucket" "backups" {
  name                        = "${var.project_name}-${var.env}-backups"
  location                    = var.region
  storage_class               = "NEARLINE"
  uniform_bucket_level_access = true
  force_destroy               = false

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = var.env == "prod" ? 90 : 30 }
  }

  labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

resource "google_storage_bucket_iam_member" "vm_uploads_rw" {
  bucket = google_storage_bucket.uploads.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.vm_service_account_email}"
}

resource "google_storage_bucket_iam_member" "vm_backups_rw" {
  bucket = google_storage_bucket.backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.vm_service_account_email}"
}
