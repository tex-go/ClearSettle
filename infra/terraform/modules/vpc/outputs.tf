output "network_id"                { value = google_compute_network.vpc.id }
output "network_name"              { value = google_compute_network.vpc.name }
output "subnet_id"                 { value = google_compute_subnetwork.app.id }
output "subnet_name"               { value = google_compute_subnetwork.app.name }
output "sql_vpc_peering_id"        { value = google_service_networking_connection.sql_vpc_peering.id }
