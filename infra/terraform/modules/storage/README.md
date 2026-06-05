# module: storage

Creates three Cloud Storage buckets with versioning, lifecycle policies, and IAM bindings.

## Buckets

| Bucket | Purpose | Lifecycle |
|---|---|---|
| `{project}-{env}-reports` | Generated settlement / reconciliation reports | STANDARD → NEARLINE@90d, delete archived@730d |
| `{project}-{env}-exports` | User-requested CSV/XLSX data exports | STANDARD → NEARLINE@90d, delete@365d |
| `{project}-{env}-audit` | Immutable audit trail (locked in prod) | STANDARD → NEARLINE@90d |

## FinOps Notes

- **NEARLINE transition at 90 days** reduces storage cost by ~60% for cold data.
- **Audit bucket** uses retention lock in prod to prevent accidental deletion.
- **Versioning enabled** on all buckets — archived versions expire to minimize cost.

## Usage

```hcl
module "storage" {
  source          = "../../modules/storage"
  project_id      = var.project_id
  project_name    = "clearsettle"
  env             = "prod"
  region          = "asia-south1"
  api_sa_email    = module.iam.api_sa_email
  worker_sa_email = module.iam.worker_sa_email
  job_sa_email    = module.iam.job_sa_email
  force_destroy   = false
}
```
