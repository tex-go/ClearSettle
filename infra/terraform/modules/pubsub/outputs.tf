output "topic_id" {
  description = "Full resource ID of the main Pub/Sub topic"
  value       = google_pubsub_topic.topic.id
}

output "topic_name" {
  description = "Name of the main Pub/Sub topic"
  value       = google_pubsub_topic.topic.name
}

output "dlq_topic_id" {
  description = "Full resource ID of the dead-letter topic"
  value       = google_pubsub_topic.dlq.id
}

output "subscription_name" {
  description = "Name of the push or pull subscription"
  value       = var.push_endpoint != "" ? google_pubsub_subscription.push[0].name : google_pubsub_subscription.pull[0].name
}
