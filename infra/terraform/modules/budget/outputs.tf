output "budget_name" {
  description = "Name of the billing budget"
  value       = google_billing_budget.budget.name
}

output "budget_id" {
  description = "Full resource ID of the billing budget"
  value       = google_billing_budget.budget.id
}
