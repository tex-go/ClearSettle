# ── Fill these in before running terraform apply ──────────────────────────────
project_id  = "YOUR_GCP_PROJECT_ID"
alert_email = "sudo.ranjith@gmail.com"
github_repo = "tex-go/ClearSettle"

# db_password is NOT stored here.
# Pass via: terraform apply -var="db_password=$(openssl rand -base64 32)"
