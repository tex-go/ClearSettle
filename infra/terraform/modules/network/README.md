# module: network

Creates the VPC foundation for a serverless ClearSettle environment.

## Resources

| Resource | Description |
|---|---|
| `google_compute_network` | Custom-mode VPC |
| `google_compute_subnetwork` | Application subnet with Private Google Access |
| `google_compute_global_address` | /16 reserved range for Cloud SQL private service access |
| `google_service_networking_connection` | Private Service Access peering for Cloud SQL |
| `google_vpc_access_connector` | Serverless VPC Connector — bridges Cloud Run → Cloud SQL |
| `google_compute_firewall` (×4) | allow-internal, allow-connector, allow-health-checks, deny-all |

## Architecture

```
Internet
    │
    ▼
Cloud Run  ──[VPC Connector]──▶  VPC  ──▶  Cloud SQL (private IP)
(Public)                       (private)
```

Cloud Run services run in Google-managed infrastructure outside the VPC.
The Serverless VPC Connector provides a bridge so Cloud Run can reach
Cloud SQL via its private IP without exposing the database to the internet.

## Usage

```hcl
module "network" {
  source          = "../../modules/network"
  project_id      = var.project_id
  project_name    = var.project_name
  env             = "prod"
  region          = "asia-south1"
  app_subnet_cidr = "10.10.0.0/24"
  connector_cidr  = "10.10.1.0/28"
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `project_id` | string | — | GCP project ID |
| `project_name` | string | — | Short slug used in resource names |
| `env` | string | — | dev / staging / prod |
| `region` | string | `asia-south1` | GCP region |
| `app_subnet_cidr` | string | — | CIDR for application subnet |
| `connector_cidr` | string | — | /28 CIDR for VPC connector (no overlap) |
| `connector_min_instances` | number | `2` | Min connector instances |
| `connector_max_instances` | number | `3` | Max connector instances |
| `connector_machine_type` | string | `e2-micro` | Connector VM size |

## Outputs

| Name | Description |
|---|---|
| `vpc_id` | VPC self-link (use as `vpc_network_id` in cloud_sql) |
| `vpc_self_link` | VPC self-link URL |
| `vpc_name` | VPC name |
| `subnet_id` | Subnet self-link |
| `connector_id` | VPC connector ID (pass to cloudrun modules) |
| `sql_peering_id` | PSA connection ID (use in cloud_sql `depends_on`) |
