output "api_url" {
  description = "Cloud Run API service URL"
  value       = module.api.service_uri
}

output "worker_url" {
  value = module.worker.service_uri
}

output "db_connection_name" {
  value = module.cloud_sql.connection_name
}

output "db_private_ip" {
  value = module.cloud_sql.private_ip
}

output "vpc_connector_id" {
  value = module.network.connector_id
}

output "reports_bucket" {
  value = module.storage.reports_bucket_name
}

output "workload_identity_provider" {
  value = module.iam.workload_identity_provider
}

output "ci_sa_email" {
  value = module.iam.ci_sa_email
}
