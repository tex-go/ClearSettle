output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.service.name
}

output "service_uri" {
  description = "HTTPS URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.service.uri
}

output "service_id" {
  description = "Full resource ID of the Cloud Run service"
  value       = google_cloud_run_v2_service.service.id
}

output "latest_revision" {
  description = "Latest deployed revision name"
  value       = google_cloud_run_v2_service.service.latest_ready_revision
}
