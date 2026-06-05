# module: cloud_sql

Creates a PostgreSQL 15 Cloud SQL instance with private IP, automated backups,
and PITR enabled for production.

## Tier Defaults

| Environment | Tier | Backups | PITR | Deletion Protection |
|---|---|---|---|---|
| dev | db-f1-micro | 7 days | no | no |
| staging | db-g1-small | 7 days | no | no |
| prod | db-g1-small | 30 days | yes | yes |

## Usage

```hcl
module "cloud_sql" {
  source         = "../../modules/cloud_sql"
  project_id     = var.project_id
  project_name   = "clearsettle"
  env            = "prod"
  region         = "asia-south1"
  vpc_network_id = module.network.vpc_id
  vpc_peering_id = module.network.sql_peering_id
  db_tier        = "db-g1-small"
  disk_size_gb   = 20
  db_password    = var.db_password
}
```

## Outputs

| Name | Description |
|---|---|
| `instance_name` | Cloud SQL instance name |
| `connection_name` | project:region:instance (for Cloud SQL Auth Proxy) |
| `private_ip` | Private IP address |
| `database_name` | Application database name |
