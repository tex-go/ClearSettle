variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for the Cloud Run job"
  default     = "asia-south1"
}

variable "job_name" {
  type        = string
  description = "Cloud Run job name"
}

variable "image" {
  type        = string
  description = "Container image URI"
}

variable "service_account_email" {
  type        = string
  description = "Service account email for the job identity"
}

variable "vpc_connector_id" {
  type        = string
  description = "Serverless VPC connector ID for private network egress"
}

variable "cpu" {
  type        = string
  description = "CPU limit e.g. '1' or '2'"
  default     = "1"
}

variable "memory" {
  type        = string
  description = "Memory limit e.g. '512Mi' or '2Gi'"
  default     = "512Mi"
}

variable "timeout_seconds" {
  type        = number
  description = "Task execution timeout in seconds (max 86400 = 24h)"
  default     = 3600
}

variable "max_retries" {
  type        = number
  description = "Number of times to retry a failed task"
  default     = 3
}

variable "task_count" {
  type        = number
  description = "Number of parallel tasks per job execution"
  default     = 1
}

variable "parallelism" {
  type        = number
  description = "Maximum number of tasks that may run concurrently"
  default     = 1
}

variable "env_vars" {
  type        = map(string)
  description = "Plain-text environment variables"
  default     = {}
}

variable "secret_env_vars" {
  type = map(object({
    secret_name = string
    version     = optional(string, "latest")
  }))
  description = "Secret Manager secrets to inject as environment variables"
  default     = {}
}

variable "labels" {
  type        = map(string)
  description = "Labels to apply to the job"
  default     = {}
}
