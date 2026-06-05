# module: cloudrun

Reusable Cloud Run V2 service module for ClearSettle microservices.

## Design

- **Scale-to-zero** by default (`min_instances = 0`)
- **CPU throttling** when idle (`cpu_idle = true`) — saves cost between requests
- **VPC egress** via Serverless Connector for Cloud SQL private IP access
- **Secrets** injected via Secret Manager (never in TF state or env files)
- **OIDC public access** gated by `allow_public_access` flag

## Services

| Service | Name | Ingress | Public |
|---|---|---|---|
| API | `clearsettle-api` | ALL | yes |
| Worker | `clearsettle-worker` | INTERNAL | no |
| Admin | `clearsettle-admin` | INTERNAL | no |

## Usage

```hcl
module "api" {
  source = "../../modules/cloudrun"

  project_id            = var.project_id
  region                = var.region
  service_name          = "clearsettle-api"
  image                 = "${var.region}-docker.pkg.dev/${var.project_id}/clearsettle/api:latest"
  service_account_email = module.iam.api_sa_email
  vpc_connector_id      = module.network.connector_id
  ingress               = "INGRESS_TRAFFIC_ALL"
  allow_public_access   = true
  min_instances         = 0
  max_instances         = 10
  cpu                   = "1"
  memory                = "512Mi"

  env_vars = {
    ENVIRONMENT = "prod"
    LOG_LEVEL   = "INFO"
  }

  secret_env_vars = {
    DATABASE_URL = {
      secret_name = "clearsettle-prod-database-password"
      version     = "latest"
    }
    JWT_SECRET = {
      secret_name = "clearsettle-prod-jwt-secret"
      version     = "latest"
    }
  }
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `service_name` | string | — | Cloud Run service name |
| `image` | string | — | Container image URI |
| `service_account_email` | string | — | Service account identity |
| `vpc_connector_id` | string | — | VPC connector for private egress |
| `ingress` | string | `INGRESS_TRAFFIC_ALL` | Ingress traffic policy |
| `min_instances` | number | `0` | Min instances (0 = scale-to-zero) |
| `max_instances` | number | `5` | Max instances |
| `cpu_idle` | bool | `true` | Throttle CPU when idle |
| `allow_public_access` | bool | `false` | Add allUsers invoker binding |
| `secret_env_vars` | map | `{}` | Secret Manager env var mappings |

## Outputs

| Name | Description |
|---|---|
| `service_uri` | HTTPS endpoint URL |
| `service_name` | Cloud Run service name |
| `service_id` | Full resource ID |
| `latest_revision` | Latest ready revision name |
