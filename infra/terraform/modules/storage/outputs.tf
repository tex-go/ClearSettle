output "reports_bucket_name" {
  description = "Name of the reports storage bucket"
  value       = google_storage_bucket.reports.name
}

output "reports_bucket_url" {
  description = "gs:// URL of the reports bucket"
  value       = google_storage_bucket.reports.url
}

output "exports_bucket_name" {
  description = "Name of the exports storage bucket"
  value       = google_storage_bucket.exports.name
}

output "exports_bucket_url" {
  description = "gs:// URL of the exports bucket"
  value       = google_storage_bucket.exports.url
}

output "audit_bucket_name" {
  description = "Name of the audit storage bucket"
  value       = google_storage_bucket.audit.name
}

output "audit_bucket_url" {
  description = "gs:// URL of the audit bucket"
  value       = google_storage_bucket.audit.url
}
