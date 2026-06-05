# ClearSettle — GCP Infrastructure

Production-grade, serverless, pay-as-you-go GCP infrastructure for ClearSettle.

**Stack:** Terraform >= 1.8 · Cloud Run V2 · Cloud SQL · Pub/Sub · Cloud Scheduler · Cloud Storage · Secret Manager

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INTERNET                                        │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ HTTPS
                         ▼
                  ┌─────────────┐
                  │  Cloud Run  │  clearsettle-api  (public)
                  │  API        │  FastAPI · scale-to-zero
                  └──────┬──────┘
                         │ VPC Connector
                         ▼
          ┌──────────────────────────────────────────┐
          │            Private VPC                   │
          │                                          │
          │  ┌──────────┐    ┌────────────────────┐  │
          │  │ Cloud SQL │    │  Cloud Run Worker  │  │
          │  │ PostgreSQL│    │  (internal only)   │  │
          │  │ Private IP│    └─────────┬──────────┘  │
          │  └──────────┘              │              │
          └────────────────────────────│──────────────┘
                                       │ push
          ┌────────────────────────────▼──────────────┐
          │           Pub/Sub Topics                  │
          │  sync-requested · reconciliation-requested│
          │  report-uploaded · notification-requested │
          └────────────────────────────┬──────────────┘
                                       │ trigger
          ┌────────────────────────────▼──────────────┐
          │         Cloud Scheduler (cron)            │
          │  Flipkart sync 6h · Amazon sync 6h        │
          │  Daily recon · Daily P&L · Weekly audit   │
          └───────────────────────────────────────────┘

          ┌────────────────────────────────────────────┐
          │         Cloud Run Jobs                    │
          │  report-parser · marketplace-sync         │
          │  reconciliation-engine · profitability    │
          │  notification-worker                      │
          └────────────────────────────────────────────┘

          ┌────────────────────────────────────────────┐
          │         Cloud Storage                     │
          │  reports-bucket · exports-bucket          │
          │  audit-bucket (retention-locked in prod)  │
          └────────────────────────────────────────────┘
```

---

## Repository Structure

```
infra/
├── terraform/
│   ├── modules/
│   │   ├── network/          VPC + subnet + serverless connector + firewall
│   │   ├── iam/              5 service accounts + Workload Identity Federation
│   │   ├── cloudrun/         Cloud Run V2 service (reusable)
│   │   ├── cloudrun-job/     Cloud Run V2 job (reusable)
│   │   ├── pubsub/           Topic + push/pull subscription + DLQ
│   │   ├── scheduler/        Cloud Scheduler → Pub/Sub
│   │   ├── cloud_sql/        PostgreSQL with private IP
│   │   ├── storage/          3 buckets (reports, exports, audit)
│   │   ├── secrets/          Secret Manager shells + IAM bindings
│   │   ├── monitoring/       Alert policies + notification channel
│   │   ├── budget/           Billing budget alerts
│   │   └── artifact_registry/ Docker image registry
│   ├── environments/
│   │   ├── dev/              Development (scale-to-zero, db-f1-micro)
│   │   ├── staging/          Staging (db-f1-micro, all 5 schedulers)
│   │   └── prod/             Production (db-g1-small, deletion protection)
│   └── global/
│       ├── iam/              Terraform state bucket + audit logs
│       └── billing/          Budget alerts for all 3 environments
├── docs/
│   └── cloud-portability.md  GCP → AWS / Azure migration guide
└── scripts/
    ├── bootstrap-gcp.sh      First-time GCP setup
    ├── deploy.sh             Manual deploy helper
    └── rollback.sh           Emergency rollback
```

---

## Modules

### `modules/network`
- Custom VPC + private subnet
- Serverless VPC Connector (Cloud Run ↔ Cloud SQL bridge)
- Private Service Access for Cloud SQL private IP
- Firewall: allow-internal, allow-connector, allow-health-checks, deny-all

### `modules/iam`
| SA | Purpose | Key Roles |
|---|---|---|
| `api-sa` | Cloud Run API | secretmanager, cloudsql.client, pubsub.publisher |
| `worker-sa` | Cloud Run Worker | secretmanager, pubsub.subscriber, pubsub.publisher |
| `scheduler-sa` | Cloud Scheduler | pubsub.publisher, run.invoker |
| `job-sa` | Cloud Run Jobs | secretmanager, cloudsql.client, storage.objectAdmin |
| `ci-sa` | GitHub Actions | artifactregistry.writer, run.admin |

WIF (Workload Identity Federation) enables keyless GitHub Actions auth.

### `modules/cloudrun`
- Cloud Run V2 service
- Scale-to-zero (`min_instances = 0`)
- CPU throttling when idle (`cpu_idle = true` for APIs)
- Secret Manager env var injection (never in TF state)
- VPC connector for private DB access

### `modules/cloudrun-job`
- Cloud Run V2 job for batch processing
- Configurable timeout, retries, parallelism
- Same secret + VPC pattern as service

### `modules/pubsub`
- Topic + push OR pull subscription
- Dead-letter topic + pull subscription
- Retry policy: 10s–600s backoff, 5 attempts max
- OIDC token auth for push subscriptions

### `modules/scheduler`
- Cloud Scheduler → Pub/Sub publish
- Cron in `Asia/Kolkata` timezone
- Configurable `paused` (dev defaults to paused)

### `modules/cloud_sql`
- PostgreSQL 15, private IP only
- Auto backups + PITR (prod)
- Deletion protection (prod)
- Query Insights enabled

### `modules/storage`
| Bucket | Class | Transition | Purpose |
|---|---|---|---|
| `reports` | STANDARD → NEARLINE @90d | delete archived @730d | Generated reports |
| `exports` | STANDARD → NEARLINE @90d | delete @365d | User data exports |
| `audit` | STANDARD → NEARLINE @90d | locked in prod | Audit trail |

### `modules/secrets`
7 secrets: `database-password`, `jwt-secret`, `flipkart-api-key`,
`flipkart-api-secret`, `amazon-api-key`, `amazon-api-secret`, `smtp-api-key`

Terraform creates shell secrets with placeholder. Populate via bootstrap script.

### `modules/monitoring`
5 alert policies: high error rate, high latency (P95), Cloud SQL CPU,
Pub/Sub backlog age, Cloud Run Job failures.

### `modules/budget`
4 thresholds: 50%, 75%, 90% current + 100% forecasted.

---

## Getting Started

### Prerequisites

- GCP project with billing enabled
- Terraform >= 1.8 installed
- `gcloud` CLI authenticated
- GitHub repository: `tex-go/ClearSettle`

### Step 1 — Bootstrap (run once)

```bash
# Create Terraform state bucket and enable APIs
./infra/scripts/bootstrap-gcp.sh

# Or manually:
gcloud storage buckets create gs://clearsettle-terraform-state \
  --location=ASIA --uniform-bucket-level-access

gcloud services enable \
  run.googleapis.com sqladmin.googleapis.com \
  secretmanager.googleapis.com vpcaccess.googleapis.com \
  pubsub.googleapis.com cloudscheduler.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com
```

### Step 2 — Apply global/iam (state bucket + audit config)

```bash
cd infra/terraform/global/iam
terraform init
terraform apply -var="project_id=YOUR_PROJECT_ID" -var="ci_sa_email=..."
```

### Step 3 — Apply an environment

```bash
cd infra/terraform/environments/prod
cp terraform.tfvars.example terraform.tfvars  # fill in project_id
terraform init
terraform apply -var="db_password=$(openssl rand -base64 32)"
```

### Step 4 — Populate secrets

```bash
# Database password
DB_PASS=$(openssl rand -base64 32)
echo -n "$DB_PASS" | gcloud secrets versions add clearsettle-prod-database-password --data-file=-

# JWT secret
echo -n "$(openssl rand -base64 64)" | gcloud secrets versions add clearsettle-prod-jwt-secret --data-file=-

# Marketplace API keys (get from Flipkart/Amazon seller accounts)
echo -n "FK_API_KEY" | gcloud secrets versions add clearsettle-prod-flipkart-api-key --data-file=-
```

### Step 5 — Configure GitHub Actions

Add these repository secrets:

| Secret | Value |
|---|---|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_WIF_PROVIDER` | From `terraform output workload_identity_provider` |
| `GCP_CI_SA_EMAIL` | From `terraform output ci_sa_email` |
| `GCP_REGION` | `asia-south1` |
| `DB_PASSWORD` | Your database password |

Push to `main` → triggers `terraform-apply.yml` → deploys prod.
Open a PR → triggers `terraform-plan.yml` → posts plan as PR comment.

---

## Environment Tiers

| | dev | staging | prod |
|---|---|---|---|
| Cloud SQL | db-f1-micro | db-f1-micro | db-g1-small |
| Cloud Run max | 2 | 5 | 10 |
| VPC connector | e2-micro×2 | e2-micro×3 | e2-standard-4×5 |
| PITR | no | no | yes |
| Deletion protection | no | no | yes |
| Schedulers paused | yes | no | no |
| Audit bucket locked | no | no | yes |
| Monthly budget | $20 | $50 | $200 |

---

## FinOps

**Scale-to-zero:** All Cloud Run services default to `min_instances = 0`.
At 200 sellers, the API is idle most of the time — Cloud Run costs $0 during idle.

**CPU throttling:** `cpu_idle = true` on API services reduces CPU billing by ~80% between requests.

**Storage tiering:** STANDARD → NEARLINE at 90 days saves ~60% on cold report storage.

**Audit bucket:** NEARLINE class after 90 days; COLDLINE could be added for 365d+ data.

**Expected monthly cost at 200 sellers:** ~$50–100 USD

**Expected monthly cost at 5,000 sellers:** ~$200–400 USD (same architecture, scale up Cloud SQL tier and max instances)

---

## Cloud Portability

See [docs/cloud-portability.md](docs/cloud-portability.md) for detailed
migration playbooks to AWS and Azure without application code changes.

Key abstractions in the app layer:
- `StorageProvider` — wraps GCS / S3 / Azure Blob
- `EventBus` — wraps Pub/Sub / SQS / Service Bus
- `SecretProvider` — wraps Secret Manager / Secrets Manager / Key Vault
- `NotificationProvider` — wraps Sendgrid / SES / Azure Communications

---

## Security

- **No public database** — Cloud SQL is private IP only
- **No VM SSH** — Cloud Run is serverless, no SSH surface
- **No service account key files** — GitHub Actions uses OIDC (WIF)
- **No secrets in Terraform state** — Secret Manager values never in outputs
- **Least privilege** — each SA has only the roles it needs
- **Uniform bucket access** — no ACL bypass on storage buckets
- **Audit logging** — ADMIN_READ and DATA_WRITE audit logs enabled
- **SSL required** — Cloud SQL enforces TLS for all connections
