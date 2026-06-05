# ── Cloud Run V2 Job ──────────────────────────────────────────────────────────

resource "google_cloud_run_v2_job" "job" {
  name     = var.job_name
  location = var.region
  project  = var.project_id

  labels = merge(var.labels, {
    managed-by = "terraform"
  })

  template {
    task_count  = var.task_count
    parallelism = var.parallelism

    template {
      service_account = var.service_account_email
      timeout         = "${var.timeout_seconds}s"
      max_retries     = var.max_retries

      vpc_access {
        connector = var.vpc_connector_id
        egress    = "ALL_TRAFFIC"
      }

      containers {
        image = var.image

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }

        # Plain-text environment variables
        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        # Secret Manager-backed environment variables
        dynamic "env" {
          for_each = var.secret_env_vars
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value.secret_name
                version = env.value.version
              }
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
    ]
  }
}
