# ── Cloud Scheduler Job ───────────────────────────────────────────────────────
# Publishes a Pub/Sub message on cron schedule.
# Cloud Scheduler → Pub/Sub → (push subscription) → Cloud Run Worker / Job

resource "google_cloud_scheduler_job" "job" {
  name             = var.job_name
  description      = var.description
  schedule         = var.schedule
  time_zone        = var.time_zone
  region           = var.region
  project          = var.project_id
  attempt_deadline = "${var.attempt_deadline_seconds}s"
  paused           = var.paused

  retry_config {
    retry_count          = var.retry_count
    max_retry_duration   = var.max_retry_duration_seconds > 0 ? "${var.max_retry_duration_seconds}s" : "0s"
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
    max_doublings        = 5
  }

  pubsub_target {
    topic_name = var.pubsub_topic_id
    data       = base64encode(jsonencode(var.message_body))

    attributes = {
      scheduled = "true"
    }
  }
}
