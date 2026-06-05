variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "billing_account_id" {
  type        = string
  description = "GCP billing account ID (format: XXXXXX-XXXXXX-XXXXXX)"
}

variable "alert_email" {
  type        = string
  description = "Email address for budget alerts"
  default     = "sudo.ranjith@gmail.com"
}

variable "prod_budget_usd" {
  type        = number
  description = "Production monthly budget in USD"
  default     = 200
}

variable "staging_budget_usd" {
  type        = number
  description = "Staging monthly budget in USD"
  default     = 50
}

variable "dev_budget_usd" {
  type        = number
  description = "Dev monthly budget in USD"
  default     = 20
}
