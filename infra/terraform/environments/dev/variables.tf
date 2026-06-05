variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "project_name" {
  type    = string
  default = "clearsettle"
}

variable "env" {
  type    = string
  default = "dev"
}

variable "region" {
  type    = string
  default = "asia-south1"
}

variable "github_repo" {
  type    = string
  default = "tex-go/ClearSettle"
}

variable "alert_email" {
  type        = string
  description = "Email for alerts"
  default     = "sudo.ranjith@gmail.com"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "api_image" {
  type        = string
  description = "API container image URI"
  default     = "asia-south1-docker.pkg.dev/REPLACE_ME/clearsettle/api:latest"
}

variable "worker_image" {
  type        = string
  description = "Worker container image URI"
  default     = "asia-south1-docker.pkg.dev/REPLACE_ME/clearsettle/worker:latest"
}
