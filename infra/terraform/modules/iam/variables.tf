variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "project_name" {
  type        = string
  description = "Short project slug (used in SA account IDs)"
}

variable "env" {
  type        = string
  description = "Environment: dev | staging | prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.env)
    error_message = "env must be dev, staging, or prod."
  }
}

variable "github_repo" {
  type        = string
  description = "GitHub repository in owner/name format e.g. tex-go/ClearSettle"
}
