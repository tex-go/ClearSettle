# module: artifact_registry

Creates a Docker Artifact Registry repository for ClearSettle container images.

## Usage

```hcl
module "artifact_registry" {
  source                   = "../../modules/artifact_registry"
  project_id               = var.project_id
  project_name             = "clearsettle"
  env                      = "prod"
  region                   = "asia-south1"
  ci_service_account_email = module.iam.ci_sa_email
}
```

## Image Naming Convention

```
asia-south1-docker.pkg.dev/{PROJECT_ID}/clearsettle/api:{TAG}
asia-south1-docker.pkg.dev/{PROJECT_ID}/clearsettle/worker:{TAG}
```
