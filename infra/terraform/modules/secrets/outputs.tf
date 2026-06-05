output "secret_ids" {
  description = "Map of secret name → full Secret Manager resource ID"
  value       = { for k, v in google_secret_manager_secret.secrets : k => v.id }
}

output "secret_names" {
  description = "Map of secret name → Secret Manager secret_id (short name)"
  value       = { for k, v in google_secret_manager_secret.secrets : k => v.secret_id }
}
