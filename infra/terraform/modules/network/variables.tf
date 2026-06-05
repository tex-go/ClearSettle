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

variable "app_subnet_cidr" {
  type        = string
  description = "CIDR block for the application subnet"
}

variable "connector_cidr" {
  type        = string
  description = "CIDR /28 for the Serverless VPC Connector (must not overlap with app_subnet_cidr)"
}

variable "connector_min_instances" {
  type        = number
  description = "Minimum number of connector instances"
  default     = 2
}

variable "connector_max_instances" {
  type        = number
  description = "Maximum number of connector instances"
  default     = 3
}

variable "connector_machine_type" {
  type        = string
  description = "Machine type for VPC Access connector instances"
  default     = "e2-micro"
}
