output "instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.postgres.name
}

output "connection_name" {
  description = "Cloud SQL connection name (project:region:instance) for Cloud SQL Auth Proxy"
  value       = google_sql_database_instance.postgres.connection_name
}

output "private_ip" {
  description = "Private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "database_name" {
  description = "Application database name"
  value       = google_sql_database.clearsettle.name
}

output "database_user" {
  description = "Application database user"
  value       = google_sql_user.app_user.name
  sensitive   = false
}
