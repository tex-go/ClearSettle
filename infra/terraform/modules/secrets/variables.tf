variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "project_name" {
  type        = string
  description = "Short project slug used in secret IDs"
}

variable "env" {
  type        = string
  description = "Environment: dev | staging | prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.env)
    error_message = "env must be dev, staging, or prod."
  }
}

variable "api_sa_email" {
  type        = string
  description = "API service account email — granted secretAccessor on all secrets"
}

variable "worker_sa_email" {
  type        = string
  description = "Worker service account email — granted secretAccessor on all secrets"
}

variable "job_sa_email" {
  type        = string
  description = "Job service account email — granted secretAccessor on all secrets"
}
