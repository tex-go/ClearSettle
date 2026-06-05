# module: monitoring

Creates Cloud Monitoring alert policies for the ClearSettle serverless platform.

## Alert Policies

| Policy | Metric | Threshold | Duration |
|---|---|---|---|
| High Error Rate | `run.googleapis.com/request_count` (5xx) | > 1 rps | 60s |
| High Latency (P95) | `run.googleapis.com/request_latencies` | > 5000ms | 120s |
| Cloud SQL High CPU | `cloudsql.googleapis.com/database/cpu/utilization` | > 80% | 300s |
| Pub/Sub Backlog | `pubsub.googleapis.com/subscription/oldest_unacked_message_age` | > 300s | 300s |
| Cloud Run Job Failures | `run.googleapis.com/job/completed_task_attempt_count` (failed) | > 0 | 0s |

All alerts route to a single email notification channel.

## Usage

```hcl
module "monitoring" {
  source              = "../../modules/monitoring"
  project_id          = var.project_id
  env                 = "prod"
  alert_email         = "sudo.ranjith@gmail.com"
  cloud_sql_instance  = module.cloud_sql.instance_name
  latency_threshold_ms = 3000
  db_cpu_threshold    = 0.75
}
```
