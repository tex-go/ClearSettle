resource "google_compute_network" "vpc" {
  name                    = "${var.project_name}-${var.env}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "app" {
  name                     = "${var.project_name}-${var.env}-app-subnet"
  ip_cidr_range            = var.app_subnet_cidr
  region                   = var.region
  network                  = google_compute_network.vpc.id
  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Private IP range for Cloud SQL VPC peering
resource "google_compute_global_address" "sql_private_range" {
  name          = "${var.project_name}-${var.env}-sql-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "sql_vpc_peering" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.sql_private_range.name]
}

# Cloud Router for NAT (so VM can reach internet without public IP for external APIs)
resource "google_compute_router" "router" {
  name    = "${var.project_name}-${var.env}-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.project_name}-${var.env}-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# ── Firewall Rules ─────────────────────────────────────────────────────────────

# Allow HTTPS and HTTP from internet (HTTP for Let's Encrypt + redirect)
resource "google_compute_firewall" "allow_web" {
  name    = "${var.project_name}-${var.env}-allow-web"
  network = google_compute_network.vpc.id

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["clearsettle-app"]
}

# Allow SSH only via IAP (Identity-Aware Proxy) — no direct SSH from internet
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "${var.project_name}-${var.env}-allow-iap-ssh"
  network = google_compute_network.vpc.id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # IAP's source range only
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["clearsettle-app"]
}

# Allow internal traffic within VPC
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.project_name}-${var.env}-allow-internal"
  network = google_compute_network.vpc.id

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
}

# Health check probe from Google LB infrastructure (future-proofing)
resource "google_compute_firewall" "allow_health_check" {
  name    = "${var.project_name}-${var.env}-allow-health-check"
  network = google_compute_network.vpc.id

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8000"]
  }

  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
  target_tags   = ["clearsettle-app"]
}
