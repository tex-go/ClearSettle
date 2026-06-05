# ── Dead-Letter Topic ─────────────────────────────────────────────────────────

resource "google_pubsub_topic" "dlq" {
  name    = "${var.topic_name}-dlq"
  project = var.project_id

  message_retention_duration = var.dlq_retention_duration

  labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

# Pull subscription on DLQ for manual inspection / alerting
resource "google_pubsub_subscription" "dlq" {
  name    = "${var.topic_name}-dlq-sub"
  topic   = google_pubsub_topic.dlq.name
  project = var.project_id

  message_retention_duration   = var.dlq_retention_duration
  retain_acked_messages        = true
  ack_deadline_seconds         = 600
  enable_message_ordering      = false
  enable_exactly_once_delivery = false

  labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

# ── Main Topic ────────────────────────────────────────────────────────────────

resource "google_pubsub_topic" "topic" {
  name    = var.topic_name
  project = var.project_id

  message_retention_duration = var.message_retention_duration

  labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

# ── Push Subscription (Cloud Run worker) ─────────────────────────────────────
# Created when push_endpoint is provided.

resource "google_pubsub_subscription" "push" {
  count   = var.push_endpoint != "" ? 1 : 0
  name    = "${var.topic_name}-push-sub"
  topic   = google_pubsub_topic.topic.name
  project = var.project_id

  ack_deadline_seconds         = var.ack_deadline_seconds
  message_retention_duration   = var.subscription_retention_duration
  retain_acked_messages        = false
  enable_message_ordering      = false
  enable_exactly_once_delivery = false

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = var.max_delivery_attempts
  }

  push_config {
    push_endpoint = var.push_endpoint

    oidc_token {
      service_account_email = var.push_service_account_email
      audience              = var.push_endpoint
    }
  }

  labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

# ── Pull Subscription ─────────────────────────────────────────────────────────
# Created when push_endpoint is NOT provided (worker polls).

resource "google_pubsub_subscription" "pull" {
  count   = var.push_endpoint == "" ? 1 : 0
  name    = "${var.topic_name}-pull-sub"
  topic   = google_pubsub_topic.topic.name
  project = var.project_id

  ack_deadline_seconds         = var.ack_deadline_seconds
  message_retention_duration   = var.subscription_retention_duration
  retain_acked_messages        = false
  enable_message_ordering      = false
  enable_exactly_once_delivery = false

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = var.max_delivery_attempts
  }

  labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

# ── DLQ subscriber needs Pub/Sub SA editor on the DLQ topic ──────────────────
# Required for dead-letter forwarding to work.

data "google_project" "project" {
  project_id = var.project_id
}

resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.dlq.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription_iam_member" "dlq_subscriber" {
  project      = var.project_id
  subscription = var.push_endpoint != "" ? google_pubsub_subscription.push[0].name : google_pubsub_subscription.pull[0].name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
