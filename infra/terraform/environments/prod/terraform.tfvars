# ── Fill these in before running terraform apply ──────────────────────────────
project_id   = "YOUR_GCP_PROJECT_ID"
domain       = "app.clearsettle.in"
alert_email  = "sudo.ranjith@gmail.com"
github_repo  = "tex-go/ClearSettle"

# db_password is intentionally NOT stored here.
# Pass it via:  terraform apply -var="db_password=$(openssl rand -base64 32)"
# Or store it in Secret Manager and reference it.
