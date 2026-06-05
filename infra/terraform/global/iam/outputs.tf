output "terraform_state_bucket" {
  description = "GCS bucket name for Terraform remote state"
  value       = google_storage_bucket.tf_state.name
}

output "terraform_state_bucket_url" {
  description = "gs:// URL of the Terraform state bucket"
  value       = google_storage_bucket.tf_state.url
}
