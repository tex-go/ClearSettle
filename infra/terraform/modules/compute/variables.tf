variable "project_id"             { type = string }
variable "project_name"           { type = string }
variable "env"                    { type = string }
variable "region"                 { type = string }
variable "zone"                   { type = string }
variable "machine_type"           { type = string  default = "e2-standard-2" }
variable "disk_size_gb"           { type = number  default = 50 }
variable "subnet_id"              { type = string }
variable "service_account_email"  { type = string }
variable "artifact_registry_name" { type = string }
variable "domain"                 { type = string }
variable "db_private_ip"          { type = string  default = "" }
variable "alert_email"            { type = string }
