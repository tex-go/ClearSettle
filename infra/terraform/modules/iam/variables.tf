variable "project_id"   { type = string }
variable "project_name" { type = string }
variable "env"          { type = string }
variable "github_repo"  {
  type        = string
  description = "GitHub repo in owner/name format e.g. tex-go/ClearSettle"
}
