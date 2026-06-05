locals {
  secret_names = [
    "database-password",
    "jwt-secret",
    "flipkart-api-key",
    "flipkart-api-secret",
    "amazon-api-key",
    "amazon-api-secret",
    "smtp-api-key",
  ]

  # Service accounts that need to read secrets at runtime
  accessor_accounts = compact([
    var.api_sa_email,
    var.worker_sa_email,
    var.job_sa_email,
  ])
}

# ── Secret shells ─────────────────────────────────────────────────────────────
# Creates the secret resource. Actual values are populated via bootstrap script
# or CI pipeline — never stored in Terraform state.

resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(local.secret_names)
  secret_id = "${var.project_name}-${var.env}-${each.value}"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

# Placeholder version so the secret exists and Cloud Run can reference it.
# Real value is set via: gcloud secrets versions add <SECRET_ID> --data-file=-
resource "google_secret_manager_secret_version" "placeholder" {
  for_each    = google_secret_manager_secret.secrets
  secret      = each.value.id
  secret_data = "REPLACE_ME"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

# ── IAM bindings — least-privilege per-secret access ─────────────────────────
# Each runtime service account gets secretAccessor on every secret in this env.
# For finer-grained control, bind per-secret per-SA instead.

locals {
  sa_secret_bindings = flatten([
    for sa in local.accessor_accounts : [
      for secret_name in local.secret_names : {
        sa          = sa
        secret_name = secret_name
        key         = "${sa}/${secret_name}"
      }
    ]
  ])
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each  = { for b in local.sa_secret_bindings : b.key => b }
  project   = var.project_id
  secret_id = google_secret_manager_secret.secrets[each.value.secret_name].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value.sa}"
}
