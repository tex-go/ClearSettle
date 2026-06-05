# ── Service Accounts ──────────────────────────────────────────────────────────

resource "google_service_account" "api" {
  account_id   = "${var.project_name}-${var.env}-api-sa"
  display_name = "ClearSettle ${var.env} API Service Account"
  description  = "Identity for Cloud Run API service"
  project      = var.project_id
}

resource "google_service_account" "worker" {
  account_id   = "${var.project_name}-${var.env}-worker-sa"
  display_name = "ClearSettle ${var.env} Worker Service Account"
  description  = "Identity for Cloud Run worker service"
  project      = var.project_id
}

resource "google_service_account" "scheduler" {
  account_id   = "${var.project_name}-${var.env}-scheduler-sa"
  display_name = "ClearSettle ${var.env} Scheduler Service Account"
  description  = "Identity for Cloud Scheduler (publishes Pub/Sub messages)"
  project      = var.project_id
}

resource "google_service_account" "job" {
  account_id   = "${var.project_name}-${var.env}-job-sa"
  display_name = "ClearSettle ${var.env} Job Service Account"
  description  = "Identity for Cloud Run Jobs (batch processing)"
  project      = var.project_id
}

resource "google_service_account" "ci" {
  account_id   = "${var.project_name}-ci-sa"
  display_name = "ClearSettle CI/CD Service Account"
  description  = "Identity for GitHub Actions — push images, deploy Cloud Run"
  project      = var.project_id
}

# ── API Service Account — least-privilege roles ───────────────────────────────

locals {
  api_roles = [
    "roles/secretmanager.secretAccessor",
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/pubsub.publisher",
    "roles/cloudtrace.agent",
  ]

  worker_roles = [
    "roles/secretmanager.secretAccessor",
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/pubsub.subscriber",
    "roles/pubsub.publisher",
    "roles/cloudtrace.agent",
  ]

  scheduler_roles = [
    "roles/pubsub.publisher",
    "roles/run.invoker",
    "roles/logging.logWriter",
  ]

  job_roles = [
    "roles/secretmanager.secretAccessor",
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent",
  ]

  ci_roles = [
    "roles/artifactregistry.writer",
    "roles/run.admin",
    "roles/iam.serviceAccountUser",
    "roles/storage.objectAdmin",
  ]
}

resource "google_project_iam_member" "api" {
  for_each = toset(local.api_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "worker" {
  for_each = toset(local.worker_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "scheduler" {
  for_each = toset(local.scheduler_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_project_iam_member" "job" {
  for_each = toset(local.job_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.job.email}"
}

resource "google_project_iam_member" "ci" {
  for_each = toset(local.ci_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.ci.email}"
}

# ── Workload Identity Federation (GitHub Actions — keyless auth) ───────────────

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "${var.project_name}-github-pool"
  display_name              = "GitHub Actions Pool"
  description               = "OIDC pool for keyless GitHub Actions authentication"
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
    "attribute.ref"        = "assertion.ref"
  }

  attribute_condition = "attribute.repository == \"${var.github_repo}\""
}

resource "google_service_account_iam_member" "ci_wif_binding" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}
