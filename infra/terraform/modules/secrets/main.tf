locals {
  secret_names = [
    "secret-key",
    "db-password",
    "encryption-key",
    "sp-api-client-id",
    "sp-api-client-secret",
    "sp-api-refresh-token",
    "anthropic-api-key",
  ]
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(local.secret_names)
  secret_id = "clearsettle-${var.env}-${each.value}"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

# Bootstrap placeholder versions so the secret exists. Real values are set via:
#   gcloud secrets versions add clearsettle-prod-secret-key --data-file=./secret.txt
# or via the bootstrap script infra/scripts/bootstrap-gcp.sh
resource "google_secret_manager_secret_version" "placeholder" {
  for_each    = google_secret_manager_secret.secrets
  secret      = each.value.id
  secret_data = "REPLACE_ME"

  lifecycle {
    ignore_changes = [secret_data]
  }
}
