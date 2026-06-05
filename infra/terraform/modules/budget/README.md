# module: budget

Creates a Cloud Billing Budget with alert thresholds at 50%, 75%, 90%, and 100%.

## Alert Thresholds

| Threshold | Basis | Action |
|---|---|---|
| 50% | Current spend | Informational email |
| 75% | Current spend | Warning email |
| 90% | Current spend | Alert email |
| 100% | Forecasted spend | Critical alert (fires before overage) |

The 100% threshold uses `FORECASTED_SPEND` so you are alerted before the
budget is actually exceeded — giving time to react.

## FinOps Expected Budgets

| Environment | Expected Monthly (USD) |
|---|---|
| dev | $10–20 |
| staging | $20–50 |
| prod (200 sellers) | $50–150 |
| prod (5,000 sellers) | $200–500 |

## Usage

```hcl
module "budget" {
  source             = "../../modules/budget"
  billing_account_id = var.billing_account_id
  project_id         = var.project_id
  env                = "prod"
  budget_amount_usd  = 200
  alert_email        = "sudo.ranjith@gmail.com"
}
```

## IAM Note

The Terraform service account requires `roles/billing.admin` or
`roles/billing.costsManager` to create billing budgets.
