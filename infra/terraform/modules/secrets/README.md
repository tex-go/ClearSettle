# module: secrets

Creates Secret Manager secrets for ClearSettle runtime credentials.

## Secrets

| Secret ID | Description |
|---|---|
| `{project}-{env}-database-password` | PostgreSQL password for the clearsettle user |
| `{project}-{env}-jwt-secret` | JWT signing secret for API authentication |
| `{project}-{env}-flipkart-api-key` | Flipkart Seller API key |
| `{project}-{env}-flipkart-api-secret` | Flipkart Seller API secret |
| `{project}-{env}-amazon-api-key` | Amazon SP-API client ID |
| `{project}-{env}-amazon-api-secret` | Amazon SP-API client secret / refresh token |
| `{project}-{env}-smtp-api-key` | SMTP relay API key for transactional email |

## Populating Secrets

Terraform creates the secret shells with a `REPLACE_ME` placeholder.
Real values must be set out-of-band:

```bash
# Using gcloud
echo -n "my-password" | gcloud secrets versions add \
  clearsettle-prod-database-password --data-file=-

# Using the bootstrap script
./infra/scripts/bootstrap-gcp.sh
```

Terraform uses `ignore_changes = [secret_data]` so subsequent `apply` runs
won't overwrite values set by the bootstrap script or operators.

## IAM

The `api_sa_email`, `worker_sa_email`, and `job_sa_email` service accounts
are granted `roles/secretmanager.secretAccessor` on each secret individually.
Secrets are **never** in Terraform outputs — they are injected as environment
variables directly by Cloud Run via Secret Manager references.

## Usage

```hcl
module "secrets" {
  source          = "../../modules/secrets"
  project_id      = var.project_id
  project_name    = "clearsettle"
  env             = "prod"
  api_sa_email    = module.iam.api_sa_email
  worker_sa_email = module.iam.worker_sa_email
  job_sa_email    = module.iam.job_sa_email
}
```
