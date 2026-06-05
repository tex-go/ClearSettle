variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "terraform_state_bucket" {
  type        = string
  description = "GCS bucket name for Terraform remote state"
  default     = "clearsettle-terraform-state"
}

variable "ci_sa_email" {
  type        = string
  description = "CI service account email — granted storage access to TF state bucket"
}
