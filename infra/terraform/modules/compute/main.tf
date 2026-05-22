resource "google_compute_address" "static_ip" {
  name   = "${var.project_name}-${var.env}-ip"
  region = var.region
}

resource "google_compute_instance" "app" {
  name         = "${var.project_name}-${var.env}-vm"
  machine_type = var.machine_type
  zone         = var.zone

  tags = ["clearsettle-app"]

  boot_disk {
    initialize_params {
      image  = "debian-cloud/debian-12"
      size   = var.disk_size_gb
      type   = "pd-ssd"
    }
  }

  network_interface {
    subnetwork = var.subnet_id
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  service_account {
    email  = var.service_account_email
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin        = "TRUE"
    enable-osconfig       = "TRUE"
    google-logging-enabled  = "TRUE"
    google-monitoring-enabled = "TRUE"
  }

  metadata_startup_script = templatefile("${path.module}/startup.sh.tpl", {
    project_id      = var.project_id
    project_name    = var.project_name
    env             = var.env
    region          = var.region
    registry        = "${var.region}-docker.pkg.dev/${var.project_id}/${var.project_name}"
    domain          = var.domain
    db_host         = var.db_private_ip
    alert_email     = var.alert_email
  })

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  labels = {
    environment = var.env
    app         = var.project_name
    managed-by  = "terraform"
  }

  lifecycle {
    ignore_changes = [metadata_startup_script]
  }
}

# Allow VM to pull from Artifact Registry
resource "google_artifact_registry_repository_iam_member" "vm_reader" {
  provider   = google
  project    = var.project_id
  location   = var.region
  repository = var.artifact_registry_name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${var.service_account_email}"
}
