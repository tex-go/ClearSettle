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
  default = "prod"
}

variable "region" {
  type    = string
  default = "asia-south1"
}

variable "github_repo" {
  type        = string
  description = "GitHub repo owner/name"
  default     = "tex-go/ClearSettle"
}

variable "alert_email" {
  type        = string
  description = "Email for deployment + monitoring alerts"
  default     = "sudo.ranjith@gmail.com"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "billing_account_id" {
  type        = string
  description = "GCP billing account ID for budget alerts (format: XXXXXX-XXXXXX-XXXXXX)"
  default     = ""
}

variable "budget_amount_usd" {
  type        = number
  description = "Monthly budget limit in USD"
  default     = 200
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
