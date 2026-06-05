# module: iam

Manages least-privilege service accounts and Workload Identity Federation
for the serverless ClearSettle platform.

## Service Accounts

| Account | Suffix | Purpose |
|---|---|---|
| `api-sa` | `{project}-{env}-api-sa` | Cloud Run API service |
| `worker-sa` | `{project}-{env}-worker-sa` | Cloud Run worker + Pub/Sub push |
| `scheduler-sa` | `{project}-{env}-scheduler-sa` | Cloud Scheduler → Pub/Sub |
| `job-sa` | `{project}-{env}-job-sa` | Cloud Run Jobs (batch processing) |
| `ci-sa` | `{project}-ci-sa` | GitHub Actions CI/CD (shared across envs) |

## IAM Roles

### api-sa
`secretmanager.secretAccessor`, `cloudsql.client`, `storage.objectAdmin`,
`logging.logWriter`, `monitoring.metricWriter`, `pubsub.publisher`, `cloudtrace.agent`

### worker-sa
`secretmanager.secretAccessor`, `cloudsql.client`, `storage.objectAdmin`,
`logging.logWriter`, `monitoring.metricWriter`, `pubsub.subscriber`, `pubsub.publisher`, `cloudtrace.agent`

### scheduler-sa
`pubsub.publisher`, `run.invoker`, `logging.logWriter`

### job-sa
`secretmanager.secretAccessor`, `cloudsql.client`, `storage.objectAdmin`,
`logging.logWriter`, `monitoring.metricWriter`, `cloudtrace.agent`

### ci-sa
`artifactregistry.writer`, `run.admin`, `iam.serviceAccountUser`, `storage.objectAdmin`

## Workload Identity Federation

GitHub Actions authenticates via OIDC — no service account key files.
The `ci-sa` is bound to the WIF pool scoped to the `github_repo` attribute.

## Usage

```hcl
module "iam" {
  source       = "../../modules/iam"
  project_id   = var.project_id
  project_name = "clearsettle"
  env          = "prod"
  github_repo  = "tex-go/ClearSettle"
}
```

## Outputs

| Name | Description |
|---|---|
| `api_sa_email` | API Cloud Run service account |
| `worker_sa_email` | Worker Cloud Run service account |
| `scheduler_sa_email` | Scheduler service account |
| `job_sa_email` | Job service account |
| `ci_sa_email` | CI/CD service account |
| `workload_identity_provider` | Full WIF provider resource name for GitHub Actions |
