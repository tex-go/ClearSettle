variable "billing_account_id" {
  type        = string
  description = "GCP billing account ID (format: XXXXXX-XXXXXX-XXXXXX)"
}

variable "project_id" {
  type        = string
  description = "GCP project ID to scope the budget to"
}

variable "env" {
  type        = string
  description = "Environment label (dev | staging | prod)"
}

variable "budget_amount_usd" {
  type        = number
  description = "Monthly budget limit in USD"
}

variable "alert_email" {
  type        = string
  description = "Email address to receive budget threshold alerts"
}

variable "alert_pubsub_topic" {
  type        = string
  description = "Pub/Sub topic ID for programmatic budget alerts (optional, leave empty to skip)"
  default     = ""
}
