terraform {
  backend "gcs" {
    bucket = "clearsettle-terraform-state"
    prefix = "prod"
  }
}
