output "api_url" {
  description = "Cloud Run API service URL"
  value       = module.api.service_uri
}

output "worker_url" {
  description = "Cloud Run Worker service URL"
  value       = module.worker.service_uri
}

output "db_connection_name" {
  description = "Cloud SQL connection name"
  value       = module.cloud_sql.connection_name
}

output "db_private_ip" {
  description = "Cloud SQL private IP"
  value       = module.cloud_sql.private_ip
}

output "vpc_connector_id" {
  description = "Serverless VPC connector ID"
  value       = module.network.connector_id
}

output "reports_bucket" {
  description = "Reports GCS bucket name"
  value       = module.storage.reports_bucket_name
}

output "workload_identity_provider" {
  description = "WIF provider resource name (for GitHub Actions)"
  value       = module.iam.workload_identity_provider
}

output "ci_sa_email" {
  description = "CI service account email"
  value       = module.iam.ci_sa_email
}
