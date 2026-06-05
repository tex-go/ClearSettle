# ── Email Notification Channel ────────────────────────────────────────────────

resource "google_monitoring_notification_channel" "email" {
  display_name = "ClearSettle ${var.env} Alerts"
  type         = "email"
  project      = var.project_id

  labels = {
    email_address = var.alert_email
  }
}

# ── Cloud Run: High Error Rate ─────────────────────────────────────────────────

resource "google_monitoring_alert_policy" "cloudrun_high_error_rate" {
  display_name = "[${upper(var.env)}] Cloud Run — High 5xx Error Rate"
  combiner     = "OR"
  project      = var.project_id

  notification_channels = [google_monitoring_notification_channel.email.name]

  alert_strategy {
    auto_close = "1800s"
  }

  conditions {
    display_name = "5xx error rate > ${var.error_rate_threshold} rps"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.error_rate_threshold

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields    = ["resource.label.service_name"]
      }
    }
  }

  documentation {
    content   = "Cloud Run service is returning 5xx errors at a rate above ${var.error_rate_threshold} rps. Check Cloud Run logs for root cause."
    mime_type = "text/markdown"
  }
}

# ── Cloud Run: High Latency ────────────────────────────────────────────────────

resource "google_monitoring_alert_policy" "cloudrun_high_latency" {
  display_name = "[${upper(var.env)}] Cloud Run — High Latency (P95)"
  combiner     = "OR"
  project      = var.project_id

  notification_channels = [google_monitoring_notification_channel.email.name]

  alert_strategy {
    auto_close = "1800s"
  }

  conditions {
    display_name = "P95 latency > ${var.latency_threshold_ms}ms"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
      duration        = "120s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.latency_threshold_ms

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_95"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.label.service_name"]
      }
    }
  }

  documentation {
    content   = "P95 request latency for a Cloud Run service exceeded ${var.latency_threshold_ms}ms. Check for cold start issues, DB query slowness, or upstream API timeouts."
    mime_type = "text/markdown"
  }
}

# ── Cloud SQL: High CPU ────────────────────────────────────────────────────────

resource "google_monitoring_alert_policy" "cloudsql_high_cpu" {
  count        = var.cloud_sql_instance != "" ? 1 : 0
  display_name = "[${upper(var.env)}] Cloud SQL — High CPU"
  combiner     = "OR"
  project      = var.project_id

  notification_channels = [google_monitoring_notification_channel.email.name]

  alert_strategy {
    auto_close = "1800s"
  }

  conditions {
    display_name = "CPU utilization > ${var.db_cpu_threshold * 100}%"

    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\" AND resource.labels.database_id=ends_with(\"${var.cloud_sql_instance}\")"
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.db_cpu_threshold

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  documentation {
    content   = "Cloud SQL CPU utilization exceeded ${var.db_cpu_threshold * 100}%. Consider optimizing queries or upgrading the instance tier."
    mime_type = "text/markdown"
  }
}

# ── Pub/Sub: Message Backlog ───────────────────────────────────────────────────

resource "google_monitoring_alert_policy" "pubsub_backlog" {
  display_name = "[${upper(var.env)}] Pub/Sub — Message Backlog (oldest unacked)"
  combiner     = "OR"
  project      = var.project_id

  notification_channels = [google_monitoring_notification_channel.email.name]

  alert_strategy {
    auto_close = "3600s"
  }

  conditions {
    display_name = "Oldest unacked message > ${var.pubsub_backlog_threshold}s"

    condition_threshold {
      filter          = "resource.type=\"pubsub_subscription\" AND metric.type=\"pubsub.googleapis.com/subscription/oldest_unacked_message_age\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.pubsub_backlog_threshold

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
        group_by_fields    = ["resource.label.subscription_id"]
      }
    }
  }

  documentation {
    content   = "A Pub/Sub subscription has messages older than ${var.pubsub_backlog_threshold}s. The worker may be down or processing is blocked."
    mime_type = "text/markdown"
  }
}

# ── Cloud Run Jobs: Failed Executions ─────────────────────────────────────────

resource "google_monitoring_alert_policy" "cloudrun_job_failures" {
  display_name = "[${upper(var.env)}] Cloud Run Jobs — Failed Execution"
  combiner     = "OR"
  project      = var.project_id

  notification_channels = [google_monitoring_notification_channel.email.name]

  alert_strategy {
    auto_close = "3600s"
  }

  conditions {
    display_name = "Job execution failed"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_job\" AND metric.type=\"run.googleapis.com/job/completed_task_attempt_count\" AND metric.labels.result=\"failed\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_COUNT"
        group_by_fields    = ["resource.label.job_name"]
      }
    }
  }

  documentation {
    content   = "A Cloud Run Job task failed. Check the job logs for error details and retry if needed."
    mime_type = "text/markdown"
  }
}

# ── Log-based Metric: Cloud Run Requests ──────────────────────────────────────

resource "google_logging_metric" "cloudrun_requests" {
  name    = "clearsettle_${var.env}_cloudrun_requests"
  project = var.project_id
  filter  = "resource.type=\"cloud_run_revision\" AND httpRequest.status>=200"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
    display_name = "ClearSettle ${var.env} Cloud Run Requests"

    labels {
      key         = "status"
      value_type  = "INT64"
      description = "HTTP response status code"
    }
  }

  label_extractors = {
    "status" = "EXTRACT(httpRequest.status)"
  }
}
