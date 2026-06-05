output "notification_channel_id" {
  description = "ID of the email notification channel"
  value       = google_monitoring_notification_channel.email.name
}

output "error_rate_alert_name" {
  description = "Name of the high error rate alert policy"
  value       = google_monitoring_alert_policy.cloudrun_high_error_rate.name
}

output "latency_alert_name" {
  description = "Name of the high latency alert policy"
  value       = google_monitoring_alert_policy.cloudrun_high_latency.name
}
