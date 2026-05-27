variable "project_id"   { type = string }
variable "project_name" { type = string; default = "clearsettle" }
variable "env"          { type = string; default = "staging" }
variable "region"       { type = string; default = "asia-south1" }
variable "zone"         { type = string; default = "asia-south1-a" }
variable "domain"       { type = string; description = "e.g. staging.clearsettle.in" }
variable "github_repo"  { type = string; default = "tex-go/ClearSettle" }
variable "alert_email"  { type = string }
variable "db_password"  { type = string; sensitive = true }
