# module: cloudrun-job

Reusable Cloud Run V2 Job module for ClearSettle batch processing.

## Jobs

| Job | Purpose |
|---|---|
| `report-parser` | Parse uploaded marketplace reports |
| `marketplace-sync` | Fetch orders/settlements from marketplace APIs |
| `reconciliation-engine` | Run reconciliation pipeline |
| `profitability-engine` | Calculate per-order profitability |
| `notification-worker` | Send alerts, emails, webhooks |

## Usage

```hcl
module "job_reconciliation" {
  source = "../../modules/cloudrun-job"

  project_id            = var.project_id
  region                = var.region
  job_name              = "clearsettle-reconciliation-engine"
  image                 = "${var.region}-docker.pkg.dev/${var.project_id}/clearsettle/worker:latest"
  service_account_email = module.iam.job_sa_email
  vpc_connector_id      = module.network.connector_id
  timeout_seconds       = 3600
  max_retries           = 3
  cpu                   = "2"
  memory                = "2Gi"

  secret_env_vars = {
    DATABASE_URL = {
      secret_name = "clearsettle-prod-database-password"
    }
  }
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `job_name` | string | — | Cloud Run job name |
| `image` | string | — | Container image URI |
| `service_account_email` | string | — | Job identity |
| `vpc_connector_id` | string | — | VPC connector for DB access |
| `timeout_seconds` | number | `3600` | Task timeout (max 86400) |
| `max_retries` | number | `3` | Retry count on failure |
| `task_count` | number | `1` | Parallel tasks per execution |
| `cpu` | string | `"1"` | CPU limit |
| `memory` | string | `"512Mi"` | Memory limit |
