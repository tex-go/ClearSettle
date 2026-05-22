variable "project_id"   {
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
variable "zone" {
  type    = string
  default = "asia-south1-a"
}
variable "domain" {
  type        = string
  description = "Production domain e.g. app.clearsettle.in"
}
variable "github_repo" {
  type        = string
  description = "GitHub repo owner/name e.g. tex-go/ClearSettle"
  default     = "tex-go/ClearSettle"
}
variable "alert_email" {
  type        = string
  description = "Email for deployment + backup alerts"
}
variable "db_password" {
  type      = string
  sensitive = true
}
