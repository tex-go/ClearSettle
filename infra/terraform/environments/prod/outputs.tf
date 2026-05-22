output "vm_external_ip"            { value = module.compute.external_ip }
output "vm_instance_name"          { value = module.compute.instance_name }
output "vm_zone"                   { value = module.compute.zone }
output "registry_url"              { value = module.artifact_registry.registry_url }
output "db_private_ip"             { value = module.cloud_sql.private_ip }
output "db_connection_name"        { value = module.cloud_sql.connection_name }
output "ci_sa_email"               { value = module.iam.ci_sa_email }
output "vm_sa_email"               { value = module.iam.vm_sa_email }
output "workload_identity_provider" { value = module.iam.workload_identity_provider }
output "uploads_bucket"            { value = module.storage.uploads_bucket }

output "deploy_instructions" {
  value = <<-EOT
    =========================================
    NEXT STEPS AFTER terraform apply
    =========================================
    1. Point DNS A record for ${var.domain} → ${module.compute.external_ip}

    2. SSH to VM via IAP and run first-time SSL:
       gcloud compute ssh ${module.compute.instance_name} --zone=${module.compute.zone} --tunnel-through-iap
       sudo certbot --nginx -d ${var.domain} -d www.${var.domain} --email ${var.alert_email} --agree-tos -n

    3. Populate secrets (run once):
       ./infra/scripts/bootstrap-gcp.sh

    4. Add GitHub Actions secrets:
       GCP_PROJECT_ID         = ${var.project_id}
       GCP_WIF_PROVIDER       = ${module.iam.workload_identity_provider}
       GCP_CI_SA_EMAIL        = ${module.iam.ci_sa_email}
       GCP_REGISTRY           = ${module.artifact_registry.registry_url}
       GCP_VM_NAME            = ${module.compute.instance_name}
       GCP_VM_ZONE            = ${module.compute.zone}
    =========================================
  EOT
}
