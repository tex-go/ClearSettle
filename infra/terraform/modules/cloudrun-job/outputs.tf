output "job_name" {
  description = "Cloud Run job name"
  value       = google_cloud_run_v2_job.job.name
}

output "job_id" {
  description = "Full resource ID of the Cloud Run job"
  value       = google_cloud_run_v2_job.job.id
}
