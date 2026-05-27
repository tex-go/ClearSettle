resource "random_id" "db_suffix" {
  byte_length = 4
}

resource "google_sql_database_instance" "postgres" {
  name             = "${var.project_name}-${var.env}-pg-${random_id.db_suffix.hex}"
  database_version = "POSTGRES_15"
  region           = var.region

  deletion_protection = var.env == "prod" ? true : false

  settings {
    tier              = var.db_tier
    availability_type = var.env == "prod" ? "REGIONAL" : "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = var.disk_size_gb
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_network_id
      require_ssl     = true
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.env == "prod" ? true : false
      backup_retention_settings {
        retained_backups = var.env == "prod" ? 30 : 7
        retention_unit   = "COUNT"
      }
      transaction_log_retention_days = var.env == "prod" ? 7 : 3
    }

    maintenance_window {
      day          = 7
      hour         = 4
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = false
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"
    }
    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }
  }

  depends_on = [var.vpc_peering_id]
}

resource "google_sql_database" "clearsettle" {
  name     = "clearsettle"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app_user" {
  name     = "clearsettle"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}
