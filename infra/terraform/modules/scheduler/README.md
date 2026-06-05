# module: scheduler

Creates a Cloud Scheduler job that publishes a Pub/Sub message on a cron schedule.

## Architecture

```
Cloud Scheduler (cron)
    │ publishes
    ▼
Pub/Sub Topic
    │ push subscription
    ▼
Cloud Run Worker / Job
```

## Scheduled Jobs

| Job Name | Schedule | Purpose |
|---|---|---|
| `flipkart-sync-every-6-hours` | `0 */6 * * *` | Flipkart order/settlement sync |
| `amazon-sync-every-6-hours` | `30 */6 * * *` | Amazon SP-API sync |
| `daily-reconciliation` | `0 2 * * *` | Run reconciliation engine |
| `daily-profitability` | `0 3 * * *` | Run profitability engine |
| `weekly-audit-generation` | `0 4 * * 0` | Generate weekly audit report |

All times in `Asia/Kolkata` timezone.

## Usage

```hcl
module "scheduler_flipkart" {
  source = "../../modules/scheduler"

  project_id            = var.project_id
  region                = var.region
  job_name              = "flipkart-sync-every-6-hours"
  description           = "Trigger Flipkart marketplace sync"
  schedule              = "0 */6 * * *"
  time_zone             = "Asia/Kolkata"
  pubsub_topic_id       = module.topic_sync.topic_id
  service_account_email = module.iam.scheduler_sa_email
  message_body          = { platform = "flipkart" }
}
```
