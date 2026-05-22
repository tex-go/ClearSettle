resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.project_name
  description   = "ClearSettle Docker images"
  format        = "DOCKER"

  docker_config {
    immutable_tags = false
  }

  labels = {
    environment = var.env
    managed-by  = "terraform"
  }
}

# Cleanup policy: keep last 10 tagged images per service, delete untagged after 7 days
resource "google_artifact_registry_repository_iam_member" "ci_writer" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.docker.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${var.ci_service_account_email}"
}
