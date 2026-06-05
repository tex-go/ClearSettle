# ── Cloud Run V2 Service ──────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "service" {
  name     = var.service_name
  location = var.region
  project  = var.project_id
  ingress  = var.ingress

  labels = merge(var.labels, {
    managed-by = "terraform"
  })

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }

    max_instance_request_concurrency = var.concurrency
    timeout                          = "${var.request_timeout_seconds}s"

    containers {
      image = var.image

      ports {
        container_port = var.port
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        # cpu_idle = true means CPU is throttled when not handling requests.
        # This reduces cost between requests (scale-to-zero billing model).
        cpu_idle          = var.cpu_idle
        startup_cpu_boost = true
      }

      # Plain-text environment variables
      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      # Secret Manager-backed environment variables — never stored in TF state
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

      startup_probe {
        initial_delay_seconds = 0
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 30

        http_get {
          path = var.health_check_path
          port = var.port
        }
      }

      liveness_probe {
        initial_delay_seconds = 0
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3

        http_get {
          path = var.health_check_path
          port = var.port
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    ignore_changes = [
      # Allow external deployment tools to update the image without TF drift
      template[0].containers[0].image,
    ]
  }
}

# ── Public access (optional) ──────────────────────────────────────────────────

resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.allow_public_access ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
