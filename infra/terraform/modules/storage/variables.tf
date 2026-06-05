variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "project_name" {
  type        = string
  description = "Short project slug used in bucket names"
}

variable "env" {
  type        = string
  description = "Environment: dev | staging | prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.env)
    error_message = "env must be dev, staging, or prod."
  }
}

variable "region" {
  type        = string
  description = "GCP region for buckets"
  default     = "asia-south1"
}

variable "api_sa_email" {
  type        = string
  description = "API service account email — granted objectAdmin on reports and exports buckets"
}

variable "worker_sa_email" {
  type        = string
  description = "Worker service account email — granted objectAdmin on all three buckets"
}

variable "job_sa_email" {
  type        = string
  description = "Job service account email — granted objectAdmin on all three buckets"
}

variable "nearline_transition_days" {
  type        = number
  description = "Days before transitioning objects to Nearline storage class"
  default     = 90
}

variable "audit_retention_days" {
  type        = number
  description = "Minimum retention period for audit logs (retention lock)"
  default     = 365
}

variable "force_destroy" {
  type        = bool
  description = "Allow bucket deletion when non-empty (set false for prod)"
  default     = false
}
