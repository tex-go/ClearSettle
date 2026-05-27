output "instance_name"   { value = google_compute_instance.app.name }
output "instance_id"     { value = google_compute_instance.app.id }
output "external_ip"     { value = google_compute_address.static_ip.address }
output "internal_ip"     { value = google_compute_instance.app.network_interface[0].network_ip }
output "zone"            { value = google_compute_instance.app.zone }
