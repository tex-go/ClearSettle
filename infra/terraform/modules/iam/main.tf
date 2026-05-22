# ── VM Service Account ─────────────────────────────────────────────────────────
resource "google_service_account" "vm" {
  account_id   = "${var.project_name}-${var.env}-vm-sa"
  display_name = "ClearSettle ${var.env} VM Service Account"
  project      = var.project_id
}

# VM needs: Secret Manager read, Cloud SQL, Storage, Logging, Monitoring
resource "google_project_iam_member" "vm_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.vm.email}"
}
resource "google_project_iam_member" "vm_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.vm.email}"
}
resource "google_project_iam_member" "vm_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.vm.email}"
}
resource "google_project_iam_member" "vm_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.vm.email}"
}
resource "google_project_iam_member" "vm_artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.vm.email}"
}

# ── CI/CD Service Account (GitHub Actions) ────────────────────────────────────
resource "google_service_account" "ci" {
  account_id   = "${var.project_name}-ci-sa"
  display_name = "ClearSettle CI/CD Service Account"
  project      = var.project_id
}

# CI needs: push to Artifact Registry, SSH via IAP to VM
resource "google_project_iam_member" "ci_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.ci.email}"
}
resource "google_project_iam_member" "ci_iap_tunnel" {
  project = var.project_id
  role    = "roles/iap.tunnelResourceAccessor"
  member  = "serviceAccount:${google_service_account.ci.email}"
}
resource "google_project_iam_member" "ci_compute_viewer" {
  project = var.project_id
  role    = "roles/compute.viewer"
  member  = "serviceAccount:${google_service_account.ci.email}"
}
resource "google_project_iam_member" "ci_oslogin" {
  project = var.project_id
  role    = "roles/compute.osLogin"
  member  = "serviceAccount:${google_service_account.ci.email}"
}

# ── Workload Identity Federation for GitHub Actions (no key files) ────────────
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "${var.project_name}-github-pool"
  display_name              = "GitHub Actions Pool"
  project                   = var.project_id
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub OIDC Provider"
  project                            = var.project_id

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "attribute.repository == \"${var.github_repo}\""
}

resource "google_service_account_iam_member" "ci_wif_binding" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}
