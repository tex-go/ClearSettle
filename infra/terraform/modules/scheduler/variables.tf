variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for the scheduler job"
  default     = "asia-south1"
}

variable "job_name" {
  type        = string
  description = "Cloud Scheduler job name"
}

variable "description" {
  type        = string
  description = "Human-readable description of the scheduled job"
  default     = ""
}

variable "schedule" {
  type        = string
  description = "Cron schedule expression e.g. '0 */6 * * *'"
}

variable "time_zone" {
  type        = string
  description = "IANA time zone for cron evaluation"
  default     = "Asia/Kolkata"
}

variable "pubsub_topic_id" {
  type        = string
  description = "Full Pub/Sub topic resource ID e.g. projects/PROJECT/topics/TOPIC"
}

variable "message_body" {
  type        = any
  description = "JSON-serializable payload to publish with each scheduled message"
  default     = {}
}

variable "service_account_email" {
  type        = string
  description = "Service account used to authenticate Pub/Sub publish calls"
}

variable "retry_count" {
  type        = number
  description = "Number of scheduler retry attempts"
  default     = 3
}

variable "attempt_deadline_seconds" {
  type        = number
  description = "Deadline for each attempt in seconds"
  default     = 180
}

variable "max_retry_duration_seconds" {
  type        = number
  description = "Total retry window in seconds"
  default     = 0
}

variable "paused" {
  type        = bool
  description = "Whether the job is paused (useful for non-prod environments)"
  default     = false
}
