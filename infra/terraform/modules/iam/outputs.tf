output "api_sa_email" {
  description = "Email of the API service account (Cloud Run API service)"
  value       = google_service_account.api.email
}

output "worker_sa_email" {
  description = "Email of the Worker service account (Cloud Run worker + jobs)"
  value       = google_service_account.worker.email
}

output "scheduler_sa_email" {
  description = "Email of the Scheduler service account (Cloud Scheduler)"
  value       = google_service_account.scheduler.email
}

output "job_sa_email" {
  description = "Email of the Job service account (Cloud Run Jobs)"
  value       = google_service_account.job.email
}

output "ci_sa_email" {
  description = "Email of the CI/CD service account (GitHub Actions)"
  value       = google_service_account.ci.email
}

output "workload_identity_provider" {
  description = "Full WIF provider resource name — use in GitHub Actions OIDC step"
  value       = "projects/${var.project_id}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/providers/${google_iam_workload_identity_pool_provider.github.workload_identity_pool_provider_id}"
}
