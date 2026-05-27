# Staging mirrors prod but uses smaller/cheaper tiers
# e2-micro VM, db-f1-micro Cloud SQL, single-zone HA

resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com", "sqladmin.googleapis.com",
    "artifactregistry.googleapis.com", "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com", "storage.googleapis.com",
    "iap.googleapis.com", "oslogin.googleapis.com",
    "logging.googleapis.com", "monitoring.googleapis.com",
    "iam.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

module "iam" {
  source       = "../../modules/iam"
  project_id   = var.project_id
  project_name = var.project_name
  env          = var.env
  github_repo  = var.github_repo
  depends_on   = [google_project_service.apis]
}

module "vpc" {
  source          = "../../modules/vpc"
  project_name    = var.project_name
  env             = var.env
  region          = var.region
  app_subnet_cidr = "10.20.0.0/24"
  depends_on      = [google_project_service.apis]
}

module "secrets" {
  source       = "../../modules/secrets"
  project_id   = var.project_id
  project_name = var.project_name
  env          = var.env
  depends_on   = [google_project_service.apis]
}

module "artifact_registry" {
  source                   = "../../modules/artifact_registry"
  project_id               = var.project_id
  project_name             = var.project_name
  env                      = var.env
  region                   = var.region
  ci_service_account_email = module.iam.ci_sa_email
  depends_on               = [google_project_service.apis]
}

module "cloud_sql" {
  source         = "../../modules/cloud_sql"
  project_name   = var.project_name
  env            = var.env
  region         = var.region
  vpc_network_id = module.vpc.network_id
  vpc_peering_id = module.vpc.sql_vpc_peering_id
  db_tier        = "db-f1-micro"
  disk_size_gb   = 10
  db_password    = var.db_password
  depends_on     = [module.vpc]
}

module "storage" {
  source                   = "../../modules/storage"
  project_name             = var.project_name
  env                      = var.env
  region                   = var.region
  domain                   = var.domain
  vm_service_account_email = module.iam.vm_sa_email
  depends_on               = [google_project_service.apis]
}

module "compute" {
  source                  = "../../modules/compute"
  project_id              = var.project_id
  project_name            = var.project_name
  env                     = var.env
  region                  = var.region
  zone                    = var.zone
  machine_type            = "e2-small"
  disk_size_gb            = 30
  subnet_id               = module.vpc.subnet_id
  service_account_email   = module.iam.vm_sa_email
  artifact_registry_name  = module.artifact_registry.repository_id
  domain                  = var.domain
  db_private_ip           = module.cloud_sql.private_ip
  alert_email             = var.alert_email
  depends_on              = [module.vpc, module.iam, module.cloud_sql]
}
