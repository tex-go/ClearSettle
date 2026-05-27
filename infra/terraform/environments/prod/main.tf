locals {
  env          = "prod"
  project_name = var.project_name
}

# ── Enable required GCP APIs ──────────────────────────────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "sqladmin.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "storage.googleapis.com",
    "iap.googleapis.com",
    "oslogin.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "dns.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ── IAM (create SAs + WIF before other modules reference them) ────────────────
module "iam" {
  source       = "../../modules/iam"
  project_id   = var.project_id
  project_name = local.project_name
  env          = local.env
  github_repo  = var.github_repo

  depends_on = [google_project_service.apis]
}

# ── VPC ───────────────────────────────────────────────────────────────────────
module "vpc" {
  source          = "../../modules/vpc"
  project_name    = local.project_name
  env             = local.env
  region          = var.region
  app_subnet_cidr = "10.10.0.0/24"

  depends_on = [google_project_service.apis]
}

# ── Secrets (create shell, populate manually / via bootstrap script) ───────────
module "secrets" {
  source       = "../../modules/secrets"
  project_id   = var.project_id
  project_name = local.project_name
  env          = local.env

  depends_on = [google_project_service.apis]
}

# ── Artifact Registry ─────────────────────────────────────────────────────────
module "artifact_registry" {
  source                    = "../../modules/artifact_registry"
  project_id                = var.project_id
  project_name              = local.project_name
  env                       = local.env
  region                    = var.region
  ci_service_account_email  = module.iam.ci_sa_email

  depends_on = [google_project_service.apis]
}

# ── Cloud SQL ─────────────────────────────────────────────────────────────────
module "cloud_sql" {
  source         = "../../modules/cloud_sql"
  project_name   = local.project_name
  env            = local.env
  region         = var.region
  vpc_network_id = module.vpc.network_id
  vpc_peering_id = module.vpc.sql_vpc_peering_id
  db_tier        = "db-g1-small"
  disk_size_gb   = 20
  db_password    = var.db_password

  depends_on = [module.vpc, google_project_service.apis]
}

# ── Storage ───────────────────────────────────────────────────────────────────
module "storage" {
  source                  = "../../modules/storage"
  project_name            = local.project_name
  env                     = local.env
  region                  = var.region
  domain                  = var.domain
  vm_service_account_email = module.iam.vm_sa_email

  depends_on = [google_project_service.apis]
}

# ── Compute Engine VM ─────────────────────────────────────────────────────────
module "compute" {
  source                  = "../../modules/compute"
  project_id              = var.project_id
  project_name            = local.project_name
  env                     = local.env
  region                  = var.region
  zone                    = var.zone
  machine_type            = "e2-standard-2"
  disk_size_gb            = 50
  subnet_id               = module.vpc.subnet_id
  service_account_email   = module.iam.vm_sa_email
  artifact_registry_name  = module.artifact_registry.repository_id
  domain                  = var.domain
  db_private_ip           = module.cloud_sql.private_ip
  alert_email             = var.alert_email

  depends_on = [module.vpc, module.iam, module.cloud_sql, google_project_service.apis]
}
