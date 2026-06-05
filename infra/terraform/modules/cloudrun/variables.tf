variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for the Cloud Run service"
  default     = "asia-south1"
}

variable "service_name" {
  type        = string
  description = "Cloud Run service name"
}

variable "image" {
  type        = string
  description = "Full container image URI e.g. asia-south1-docker.pkg.dev/PROJECT/clearsettle/api:latest"
}

variable "service_account_email" {
  type        = string
  description = "Service account email for the Cloud Run service identity"
}

variable "vpc_connector_id" {
  type        = string
  description = "Serverless VPC connector ID for private network egress"
}

variable "ingress" {
  type        = string
  description = "Ingress traffic setting: INGRESS_TRAFFIC_ALL | INGRESS_TRAFFIC_INTERNAL_ONLY | INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  default     = "INGRESS_TRAFFIC_ALL"
  validation {
    condition = contains([
      "INGRESS_TRAFFIC_ALL",
      "INGRESS_TRAFFIC_INTERNAL_ONLY",
      "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER",
    ], var.ingress)
    error_message = "ingress must be INGRESS_TRAFFIC_ALL, INGRESS_TRAFFIC_INTERNAL_ONLY, or INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER."
  }
}

variable "min_instances" {
  type        = number
  description = "Minimum number of instances (0 = scale-to-zero)"
  default     = 0
}

variable "max_instances" {
  type        = number
  description = "Maximum number of instances"
  default     = 5
}

variable "concurrency" {
  type        = number
  description = "Maximum concurrent requests per instance"
  default     = 80
}

variable "cpu" {
  type        = string
  description = "CPU limit e.g. '1' or '2'"
  default     = "1"
}

variable "memory" {
  type        = string
  description = "Memory limit e.g. '512Mi' or '1Gi'"
  default     = "512Mi"
}

variable "cpu_idle" {
  type        = bool
  description = "Throttle CPU to near-zero when not processing requests (FinOps: reduces cost between requests)"
  default     = true
}

variable "port" {
  type        = number
  description = "Container port to expose"
  default     = 8080
}

variable "request_timeout_seconds" {
  type        = number
  description = "Maximum request duration in seconds (max 3600)"
  default     = 300
}

variable "health_check_path" {
  type        = string
  description = "HTTP path for liveness and startup probes"
  default     = "/health"
}

variable "env_vars" {
  type        = map(string)
  description = "Plain-text environment variables"
  default     = {}
}

variable "secret_env_vars" {
  type = map(object({
    secret_name = string
    version     = optional(string, "latest")
  }))
  description = "Secret Manager secrets to inject as environment variables. Key = env var name."
  default     = {}
}

variable "allow_public_access" {
  type        = bool
  description = "Grant allUsers roles/run.invoker (public HTTP endpoint)"
  default     = false
}

variable "labels" {
  type        = map(string)
  description = "Labels to apply to the Cloud Run service"
  default     = {}
}
