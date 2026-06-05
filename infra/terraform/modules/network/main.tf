# ── VPC ──────────────────────────────────────────────────────────────────────

resource "google_compute_network" "vpc" {
  name                    = "${var.project_name}-${var.env}-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id
}

# ── Subnet ────────────────────────────────────────────────────────────────────

resource "google_compute_subnetwork" "app" {
  name                     = "${var.project_name}-${var.env}-app-subnet"
  ip_cidr_range            = var.app_subnet_cidr
  region                   = var.region
  network                  = google_compute_network.vpc.id
  project                  = var.project_id
  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# ── Private Service Access (for Cloud SQL private IP) ─────────────────────────

resource "google_compute_global_address" "private_service_range" {
  name          = "${var.project_name}-${var.env}-psa-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
  project       = var.project_id
}

resource "google_service_networking_connection" "sql_peering" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_service_range.name]
}

# ── Serverless VPC Connector (Cloud Run → private VPC resources) ─────────────
# Cloud Run services run outside the VPC; the connector bridges them in.

resource "google_vpc_access_connector" "connector" {
  provider      = google-beta
  name          = "${var.project_name}-${var.env}-connector"
  region        = var.region
  project       = var.project_id
  network       = google_compute_network.vpc.name
  ip_cidr_range = var.connector_cidr

  min_instances = var.connector_min_instances
  max_instances = var.connector_max_instances
  machine_type  = var.connector_machine_type
}

# ── Firewall Rules ────────────────────────────────────────────────────────────

# Allow traffic from VPC connector range to internal services (Cloud SQL port 5432)
resource "google_compute_firewall" "allow_connector_to_internal" {
  name    = "${var.project_name}-${var.env}-allow-connector-internal"
  network = google_compute_network.vpc.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["5432", "443", "80"]
  }

  source_ranges = [var.connector_cidr]
  direction     = "INGRESS"
  priority      = 1000
}

# Allow internal subnet traffic
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.project_name}-${var.env}-allow-internal"
  network = google_compute_network.vpc.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  allow {
    protocol = "icmp"
  }

  source_ranges = [var.app_subnet_cidr]
  direction     = "INGRESS"
  priority      = 1000
}

# Allow Google health check ranges (required for load balancers / serverless NEGs)
resource "google_compute_firewall" "allow_health_checks" {
  name    = "${var.project_name}-${var.env}-allow-health-checks"
  network = google_compute_network.vpc.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8080"]
  }

  source_ranges = ["35.191.0.0/16", "130.211.0.0/22"]
  direction     = "INGRESS"
  priority      = 1000
}

# Deny all other ingress (explicit default-deny over the VPC's implicit allow)
resource "google_compute_firewall" "deny_all_ingress" {
  name      = "${var.project_name}-${var.env}-deny-all-ingress"
  network   = google_compute_network.vpc.name
  project   = var.project_id
  priority  = 65534
  direction = "INGRESS"

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
}
