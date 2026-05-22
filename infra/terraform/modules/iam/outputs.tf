output "vm_sa_email"               { value = google_service_account.vm.email }
output "ci_sa_email"               { value = google_service_account.ci.email }
output "workload_identity_provider" {
  value = "projects/${var.project_id}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/providers/${google_iam_workload_identity_pool_provider.github.workload_identity_pool_provider_id}"
}
