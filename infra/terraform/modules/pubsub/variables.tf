variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "env" {
  type        = string
  description = "Environment label (dev | staging | prod)"
}

variable "topic_name" {
  type        = string
  description = "Pub/Sub topic name"
}

variable "message_retention_duration" {
  type        = string
  description = "Topic-level message retention (ISO 8601 duration)"
  default     = "86400s"
}

variable "push_endpoint" {
  type        = string
  description = "HTTPS push endpoint URL (Cloud Run service URL). Leave empty for pull subscription."
  default     = ""
}

variable "push_service_account_email" {
  type        = string
  description = "Service account email used to generate OIDC tokens for push subscription auth"
  default     = ""
}

variable "ack_deadline_seconds" {
  type        = number
  description = "Acknowledgment deadline in seconds"
  default     = 60
}

variable "max_delivery_attempts" {
  type        = number
  description = "Max delivery attempts before routing to dead-letter topic"
  default     = 5
}

variable "subscription_retention_duration" {
  type        = string
  description = "How long undelivered messages are retained (ISO 8601 duration)"
  default     = "86400s"
}

variable "dlq_retention_duration" {
  type        = string
  description = "How long dead-letter messages are retained"
  default     = "604800s"
}
