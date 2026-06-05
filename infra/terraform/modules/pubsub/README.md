# module: pubsub

Creates a Pub/Sub topic with push or pull subscription and dead-letter queue.

## Topics

| Topic | Purpose |
|---|---|
| `report-uploaded` | File uploaded → trigger report-parser job |
| `sync-requested` | Trigger marketplace-sync job |
| `reconciliation-requested` | Trigger reconciliation-engine job |
| `notification-requested` | Trigger notification-worker job |

## Architecture

```
Publisher (API / Scheduler)
    │
    ▼
[Main Topic]
    │
    ├──▶ [Push Subscription] ──▶ Cloud Run Worker  (if push_endpoint set)
    │         │ (on failure)
    │         └──▶ [DLQ Topic] ──▶ [DLQ Pull Sub]  (inspect / alert)
    │
    └──▶ [Pull Subscription]  (if no push_endpoint)
```

## Retry Policy

- Minimum backoff: 10s
- Maximum backoff: 600s
- Max delivery attempts before DLQ: 5 (configurable)
- DLQ retention: 7 days

## Usage

```hcl
module "topic_sync" {
  source     = "../../modules/pubsub"
  project_id = var.project_id
  env        = var.env
  topic_name = "sync-requested"

  push_endpoint              = module.worker.service_uri
  push_service_account_email = module.iam.worker_sa_email
  max_delivery_attempts      = 5
  ack_deadline_seconds       = 60
}
```
