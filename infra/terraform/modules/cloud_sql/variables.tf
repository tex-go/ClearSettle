variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "project_name" {
  type        = string
  description = "Short project slug used in resource names"
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
  description = "GCP region"
  default     = "asia-south1"
}

variable "vpc_network_id" {
  type        = string
  description = "VPC network self-link (used for Cloud SQL private IP)"
}

variable "vpc_peering_id" {
  type        = string
  description = "Private service connection ID (used in depends_on to ensure peering is ready)"
}

variable "db_tier" {
  type        = string
  description = "Cloud SQL machine tier: db-f1-micro | db-g1-small | db-n1-standard-1 etc."
  default     = "db-g1-small"
}

variable "disk_size_gb" {
  type        = number
  description = "Initial disk size in GB (auto-resize is enabled)"
  default     = 20
}

variable "db_password" {
  type        = string
  description = "Password for the clearsettle database user"
  sensitive   = true
}

variable "database_name" {
  type        = string
  description = "Name of the application database"
  default     = "clearsettle"
}

variable "database_user" {
  type        = string
  description = "Name of the application database user"
  default     = "clearsettle"
}
