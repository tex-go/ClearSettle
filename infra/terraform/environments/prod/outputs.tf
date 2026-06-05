output "api_url" {
  description = "Cloud Run API service URL"
  value       = module.api.service_uri
}

output "worker_url" {
  description = "Cloud Run Worker service URL"
  value       = module.worker.service_uri
}

output "admin_url" {
  description = "Cloud Run Admin service URL (internal)"
  value       = module.admin.service_uri
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

output "exports_bucket" {
  description = "Exports GCS bucket name"
  value       = module.storage.exports_bucket_name
}

output "audit_bucket" {
  description = "Audit GCS bucket name"
  value       = module.storage.audit_bucket_name
}

output "workload_identity_provider" {
  description = "WIF provider resource name (for GitHub Actions)"
  value       = module.iam.workload_identity_provider
}

output "ci_sa_email" {
  description = "CI service account email"
  value       = module.iam.ci_sa_email
}

output "api_sa_email" {
  description = "API service account email"
  value       = module.iam.api_sa_email
}

output "deploy_instructions" {
  description = "Post-apply setup instructions"
  value       = <<-EOT
    =========================================
    POST TERRAFORM APPLY — NEXT STEPS
    =========================================

    1. Populate secrets (run once):
       ./infra/scripts/bootstrap-gcp.sh

    2. Add GitHub Actions repository secrets:
       GCP_PROJECT_ID   = ${var.project_id}
       GCP_WIF_PROVIDER = ${module.iam.workload_identity_provider}
       GCP_CI_SA_EMAIL  = ${module.iam.ci_sa_email}
       GCP_REGION       = ${var.region}

    3. Update api_image and worker_image variables in terraform.tfvars
       after the first CI build pushes images.

    4. Re-run: terraform apply -var-file=terraform.tfvars

    =========================================
  EOT
}
