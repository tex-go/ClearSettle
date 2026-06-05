output "prod_budget_name" {
  description = "Production billing budget name"
  value       = module.budget_prod.budget_name
}

output "staging_budget_name" {
  description = "Staging billing budget name"
  value       = module.budget_staging.budget_name
}

output "dev_budget_name" {
  description = "Dev billing budget name"
  value       = module.budget_dev.budget_name
}
