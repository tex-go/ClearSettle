# ── Billing Budgets ───────────────────────────────────────────────────────────
# Three budgets — one per environment — all scoped to the same project.
# Alerts fire at 50%, 75%, 90%, and 100% (forecasted) of monthly limit.

module "budget_prod" {
  source             = "../../modules/budget"
  billing_account_id = var.billing_account_id
  project_id         = var.project_id
  env                = "prod"
  budget_amount_usd  = var.prod_budget_usd
  alert_email        = var.alert_email
}

module "budget_staging" {
  source             = "../../modules/budget"
  billing_account_id = var.billing_account_id
  project_id         = var.project_id
  env                = "staging"
  budget_amount_usd  = var.staging_budget_usd
  alert_email        = var.alert_email
}

module "budget_dev" {
  source             = "../../modules/budget"
  billing_account_id = var.billing_account_id
  project_id         = var.project_id
  env                = "dev"
  budget_amount_usd  = var.dev_budget_usd
  alert_email        = var.alert_email
}
