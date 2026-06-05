output "vpc_id" {
  description = "Self-link of the VPC network"
  value       = google_compute_network.vpc.id
}

output "vpc_self_link" {
  description = "Self-link URL of the VPC network"
  value       = google_compute_network.vpc.self_link
}

output "vpc_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.vpc.name
}

output "subnet_id" {
  description = "Self-link of the application subnet"
  value       = google_compute_subnetwork.app.id
}

output "subnet_name" {
  description = "Name of the application subnet"
  value       = google_compute_subnetwork.app.name
}

output "connector_id" {
  description = "Serverless VPC Connector ID (used by Cloud Run modules)"
  value       = google_vpc_access_connector.connector.id
}

output "sql_peering_id" {
  description = "ID of the private service networking connection (used by Cloud SQL depends_on)"
  value       = google_service_networking_connection.sql_peering.id
}
