variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "env" {
  type        = string
  description = "Environment: dev | staging | prod"
}

variable "alert_email" {
  type        = string
  description = "Email address for alert notifications"
}

variable "api_service_name" {
  type        = string
  description = "Cloud Run API service name"
  default     = "clearsettle-api"
}

variable "worker_service_name" {
  type        = string
  description = "Cloud Run worker service name"
  default     = "clearsettle-worker"
}

variable "cloud_sql_instance" {
  type        = string
  description = "Cloud SQL instance name (for CPU alert)"
  default     = ""
}

variable "error_rate_threshold" {
  type        = number
  description = "Cloud Run 5xx error rate threshold (requests per second)"
  default     = 1
}

variable "latency_threshold_ms" {
  type        = number
  description = "Cloud Run P95 latency threshold in milliseconds"
  default     = 5000
}

variable "db_cpu_threshold" {
  type        = number
  description = "Cloud SQL CPU utilization threshold (0.0–1.0)"
  default     = 0.8
}

variable "pubsub_backlog_threshold" {
  type        = number
  description = "Pub/Sub oldest unacked message age threshold in seconds"
  default     = 300
}
