locals {
  env          = "dev"
  project_name = var.project_name
  region       = var.region
  image_base   = "${var.region}-docker.pkg.dev/${var.project_id}/${var.project_name}"
}

# ── GCP APIs ──────────────────────────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "cloudscheduler.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "cloudbuild.googleapis.com",
  ])
  service            = each.value
  project            = var.project_id
  disable_on_destroy = false
}

# ── IAM ───────────────────────────────────────────────────────────────────────

module "iam" {
  source       = "../../modules/iam"
  project_id   = var.project_id
  project_name = local.project_name
  env          = local.env
  github_repo  = var.github_repo
  depends_on   = [google_project_service.apis]
}

# ── Network ───────────────────────────────────────────────────────────────────

module "network" {
  source          = "../../modules/network"
  project_id      = var.project_id
  project_name    = local.project_name
  env             = local.env
  region          = local.region
  app_subnet_cidr = "10.30.0.0/24"
  connector_cidr  = "10.30.1.0/28"
  depends_on      = [google_project_service.apis]
}

# ── Artifact Registry ─────────────────────────────────────────────────────────

module "artifact_registry" {
  source                   = "../../modules/artifact_registry"
  project_id               = var.project_id
  project_name             = local.project_name
  env                      = local.env
  region                   = local.region
  ci_service_account_email = module.iam.ci_sa_email
  depends_on               = [google_project_service.apis]
}

# ── Secrets ───────────────────────────────────────────────────────────────────

module "secrets" {
  source          = "../../modules/secrets"
  project_id      = var.project_id
  project_name    = local.project_name
  env             = local.env
  api_sa_email    = module.iam.api_sa_email
  worker_sa_email = module.iam.worker_sa_email
  job_sa_email    = module.iam.job_sa_email
  depends_on      = [google_project_service.apis]
}

# ── Cloud SQL ─────────────────────────────────────────────────────────────────

module "cloud_sql" {
  source         = "../../modules/cloud_sql"
  project_id     = var.project_id
  project_name   = local.project_name
  env            = local.env
  region         = local.region
  vpc_network_id = module.network.vpc_id
  vpc_peering_id = module.network.sql_peering_id
  db_tier        = "db-f1-micro"
  disk_size_gb   = 10
  db_password    = var.db_password
  depends_on     = [module.network, google_project_service.apis]
}

# ── Storage ───────────────────────────────────────────────────────────────────

module "storage" {
  source          = "../../modules/storage"
  project_id      = var.project_id
  project_name    = local.project_name
  env             = local.env
  region          = local.region
  api_sa_email    = module.iam.api_sa_email
  worker_sa_email = module.iam.worker_sa_email
  job_sa_email    = module.iam.job_sa_email
  force_destroy   = true
  depends_on      = [google_project_service.apis]
}

# ── Cloud Run: API Service ────────────────────────────────────────────────────

module "api" {
  source = "../../modules/cloudrun"

  project_id            = var.project_id
  region                = local.region
  service_name          = "${local.project_name}-api"
  image                 = var.api_image
  service_account_email = module.iam.api_sa_email
  vpc_connector_id      = module.network.connector_id
  ingress               = "INGRESS_TRAFFIC_ALL"
  allow_public_access   = true
  min_instances         = 0
  max_instances         = 2
  cpu                   = "1"
  memory                = "512Mi"
  cpu_idle              = true

  env_vars = {
    ENVIRONMENT      = local.env
    LOG_LEVEL        = "DEBUG"
    DB_HOST          = module.cloud_sql.private_ip
    DB_NAME          = module.cloud_sql.database_name
    DB_USER          = module.cloud_sql.database_user
    GCS_BUCKET_NAME  = module.storage.reports_bucket_name
    STORAGE_BACKEND  = "gcs"
  }

  secret_env_vars = {
    DB_PASSWORD = {
      secret_name = module.secrets.secret_names["database-password"]
    }
    JWT_SECRET = {
      secret_name = module.secrets.secret_names["jwt-secret"]
    }
  }

  labels     = { environment = local.env }
  depends_on = [module.network, module.iam, module.secrets, module.cloud_sql]
}

# ── Cloud Run: Worker Service ─────────────────────────────────────────────────

module "worker" {
  source = "../../modules/cloudrun"

  project_id            = var.project_id
  region                = local.region
  service_name          = "${local.project_name}-worker"
  image                 = var.worker_image
  service_account_email = module.iam.worker_sa_email
  vpc_connector_id      = module.network.connector_id
  ingress               = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  allow_public_access   = false
  min_instances         = 0
  max_instances         = 2
  cpu                   = "1"
  memory                = "512Mi"
  cpu_idle              = false

  env_vars = {
    ENVIRONMENT = local.env
    LOG_LEVEL   = "DEBUG"
    DB_HOST     = module.cloud_sql.private_ip
    DB_NAME     = module.cloud_sql.database_name
    DB_USER     = module.cloud_sql.database_user
  }

  secret_env_vars = {
    DB_PASSWORD = {
      secret_name = module.secrets.secret_names["database-password"]
    }
  }

  labels     = { environment = local.env }
  depends_on = [module.network, module.iam, module.secrets, module.cloud_sql]
}

# ── Pub/Sub Topics ────────────────────────────────────────────────────────────

module "topic_sync" {
  source                     = "../../modules/pubsub"
  project_id                 = var.project_id
  env                        = local.env
  topic_name                 = "sync-requested"
  push_endpoint              = "${module.worker.service_uri}/pubsub/sync"
  push_service_account_email = module.iam.worker_sa_email
  depends_on                 = [module.worker, google_project_service.apis]
}

module "topic_reconciliation" {
  source                     = "../../modules/pubsub"
  project_id                 = var.project_id
  env                        = local.env
  topic_name                 = "reconciliation-requested"
  push_endpoint              = "${module.worker.service_uri}/pubsub/reconciliation"
  push_service_account_email = module.iam.worker_sa_email
  depends_on                 = [module.worker, google_project_service.apis]
}

module "topic_report" {
  source                     = "../../modules/pubsub"
  project_id                 = var.project_id
  env                        = local.env
  topic_name                 = "report-uploaded"
  push_endpoint              = "${module.worker.service_uri}/pubsub/report"
  push_service_account_email = module.iam.worker_sa_email
  depends_on                 = [module.worker, google_project_service.apis]
}

module "topic_notification" {
  source                     = "../../modules/pubsub"
  project_id                 = var.project_id
  env                        = local.env
  topic_name                 = "notification-requested"
  push_endpoint              = "${module.worker.service_uri}/pubsub/notification"
  push_service_account_email = module.iam.worker_sa_email
  depends_on                 = [module.worker, google_project_service.apis]
}

# ── Cloud Run Jobs ────────────────────────────────────────────────────────────

module "job_marketplace_sync" {
  source = "../../modules/cloudrun-job"

  project_id            = var.project_id
  region                = local.region
  job_name              = "${local.project_name}-marketplace-sync"
  image                 = var.worker_image
  service_account_email = module.iam.job_sa_email
  vpc_connector_id      = module.network.connector_id
  timeout_seconds       = 1800
  max_retries           = 3
  cpu                   = "1"
  memory                = "512Mi"

  env_vars = {
    ENVIRONMENT = local.env
    JOB_TYPE    = "marketplace-sync"
    DB_HOST     = module.cloud_sql.private_ip
    DB_NAME     = module.cloud_sql.database_name
    DB_USER     = module.cloud_sql.database_user
  }

  secret_env_vars = {
    DB_PASSWORD = { secret_name = module.secrets.secret_names["database-password"] }
  }

  depends_on = [module.network, module.iam, module.secrets, module.cloud_sql]
}

module "job_reconciliation" {
  source = "../../modules/cloudrun-job"

  project_id            = var.project_id
  region                = local.region
  job_name              = "${local.project_name}-reconciliation-engine"
  image                 = var.worker_image
  service_account_email = module.iam.job_sa_email
  vpc_connector_id      = module.network.connector_id
  timeout_seconds       = 3600
  max_retries           = 2
  cpu                   = "1"
  memory                = "1Gi"

  env_vars = {
    ENVIRONMENT = local.env
    JOB_TYPE    = "reconciliation"
    DB_HOST     = module.cloud_sql.private_ip
    DB_NAME     = module.cloud_sql.database_name
    DB_USER     = module.cloud_sql.database_user
  }

  secret_env_vars = {
    DB_PASSWORD = { secret_name = module.secrets.secret_names["database-password"] }
  }

  depends_on = [module.network, module.iam, module.secrets, module.cloud_sql]
}

# ── Cloud Scheduler (paused in dev by default) ────────────────────────────────

module "scheduler_flipkart_sync" {
  source = "../../modules/scheduler"

  project_id            = var.project_id
  region                = local.region
  job_name              = "flipkart-sync-every-6-hours"
  description           = "Trigger Flipkart marketplace sync"
  schedule              = "0 */6 * * *"
  time_zone             = "Asia/Kolkata"
  pubsub_topic_id       = module.topic_sync.topic_id
  service_account_email = module.iam.scheduler_sa_email
  message_body          = { platform = "flipkart", env = local.env }
  paused                = true

  depends_on = [module.topic_sync, module.iam]
}

module "scheduler_amazon_sync" {
  source = "../../modules/scheduler"

  project_id            = var.project_id
  region                = local.region
  job_name              = "amazon-sync-every-6-hours"
  description           = "Trigger Amazon SP-API sync"
  schedule              = "30 */6 * * *"
  time_zone             = "Asia/Kolkata"
  pubsub_topic_id       = module.topic_sync.topic_id
  service_account_email = module.iam.scheduler_sa_email
  message_body          = { platform = "amazon", env = local.env }
  paused                = true

  depends_on = [module.topic_sync, module.iam]
}

# ── Monitoring ────────────────────────────────────────────────────────────────

module "monitoring" {
  source             = "../../modules/monitoring"
  project_id         = var.project_id
  env                = local.env
  alert_email        = var.alert_email
  cloud_sql_instance = module.cloud_sql.instance_name
  depends_on         = [google_project_service.apis]
}
