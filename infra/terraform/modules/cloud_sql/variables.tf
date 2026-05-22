variable "project_name"   { type = string }
variable "env"            { type = string }
variable "region"         { type = string }
variable "vpc_network_id" { type = string }
variable "vpc_peering_id" { type = string }
variable "db_tier"        { type = string  default = "db-g1-small" }
variable "disk_size_gb"   { type = number  default = 20 }
variable "db_password"    {
  type      = string
  sensitive = true
}
