#!/usr/bin/env bash
# ============================================================================
# bootstrap-gcp.sh — One-time GCP project setup
# Run this ONCE after `terraform apply` to:
#   1. Create the Terraform state bucket
#   2. Populate all secrets in Secret Manager
#   3. Enable required APIs
#   4. Create the deploy SSH key pair
#
# Usage: ./infra/scripts/bootstrap-gcp.sh
# ============================================================================
set -euo pipefail

# ── Config — edit these ───────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-YOUR_GCP_PROJECT_ID}"
REGION="${GCP_REGION:-asia-south1}"
ENV="${DEPLOY_ENV:-prod}"

echo "=== ClearSettle GCP Bootstrap ==="
echo "Project: $PROJECT_ID | Region: $REGION | Env: $ENV"

# ── 1. Authenticate ───────────────────────────────────────────────────────────
gcloud auth login --quiet 2>/dev/null || true
gcloud config set project "$PROJECT_ID"

# ── 2. Enable APIs (Terraform will also do this, but bootstrap needs them first)
echo "Enabling required APIs..."
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  --project="$PROJECT_ID"

# ── 3. Terraform state bucket ─────────────────────────────────────────────────
BUCKET="clearsettle-terraform-state"
if ! gsutil ls "gs://$BUCKET" &>/dev/null; then
  echo "Creating Terraform state bucket: gs://$BUCKET"
  gcloud storage buckets create "gs://$BUCKET" \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    --uniform-bucket-level-access
  gcloud storage buckets update "gs://$BUCKET" --versioning
else
  echo "State bucket already exists: gs://$BUCKET"
fi

# ── 4. Populate secrets ───────────────────────────────────────────────────────
set_secret() {
  local NAME="$1"
  local PROMPT="$2"
  local SECRET_ID="clearsettle-${ENV}-${NAME}"

  # Check if a real value already exists (not placeholder)
  CURRENT=$(gcloud secrets versions access latest --secret="$SECRET_ID" \
    --project="$PROJECT_ID" 2>/dev/null || echo "")
  if [ "$CURRENT" != "REPLACE_ME" ] && [ -n "$CURRENT" ]; then
    echo "  $SECRET_ID — already set, skipping"
    return
  fi

  read -rsp "  Enter $PROMPT: " VALUE
  echo
  if [ -n "$VALUE" ]; then
    echo -n "$VALUE" | gcloud secrets versions add "$SECRET_ID" \
      --data-file=- --project="$PROJECT_ID"
    echo "  ✓ $SECRET_ID updated"
  else
    echo "  ⚠ Skipped $SECRET_ID (empty input)"
  fi
}

echo ""
echo "=== Populating secrets ==="
echo "  (Press Enter to skip if already set)"

set_secret "secret-key"            "Django/JWT SECRET_KEY (run: python -c \"import secrets; print(secrets.token_hex(32))\")"
set_secret "db-password"           "PostgreSQL password (min 20 chars, alphanumeric)"
set_secret "encryption-key"        "Fernet ENCRYPTION_KEY (run: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")"
set_secret "sp-api-client-id"      "Amazon SP-API Client ID"
set_secret "sp-api-client-secret"  "Amazon SP-API Client Secret"
set_secret "sp-api-refresh-token"  "Amazon SP-API Refresh Token (optional — can be set later)"
set_secret "anthropic-api-key"     "Anthropic API Key (optional — can be set later)"

# ── 5. Redis password ─────────────────────────────────────────────────────────
REDIS_SECRET="clearsettle-${ENV}-redis-password"
if ! gcloud secrets describe "$REDIS_SECRET" --project="$PROJECT_ID" &>/dev/null; then
  REDIS_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  gcloud secrets create "$REDIS_SECRET" --project="$PROJECT_ID" \
    --replication-policy="automatic"
  echo -n "$REDIS_PASS" | gcloud secrets versions add "$REDIS_SECRET" \
    --data-file=- --project="$PROJECT_ID"
  echo "  ✓ Redis password generated and stored"
fi

# ── 6. Deploy SSH key pair for GitHub Actions ─────────────────────────────────
KEY_DIR="$HOME/.ssh"
KEY_FILE="$KEY_DIR/clearsettle-deploy"

if [ ! -f "$KEY_FILE" ]; then
  echo ""
  echo "=== Generating deploy SSH key pair ==="
  ssh-keygen -t ed25519 -C "clearsettle-deploy@github-actions" \
    -f "$KEY_FILE" -N ""
  echo ""
  echo "PUBLIC KEY (add to VM via OS Login or metadata):"
  cat "${KEY_FILE}.pub"
  echo ""
  echo "PRIVATE KEY (add as GitHub Secret GCP_DEPLOY_SSH_KEY):"
  cat "$KEY_FILE"
  echo ""
  echo "⚠ The private key above will not be shown again. Save it now."
else
  echo "Deploy key already exists at $KEY_FILE"
fi

# ── 7. GitHub Secrets reminder ────────────────────────────────────────────────
echo ""
echo "=== GitHub Repository Secrets to add ==="
echo "  Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "  GCP_PROJECT_ID        = $PROJECT_ID"
echo "  GCP_REGION            = $REGION"
echo "  GCP_WIF_PROVIDER      = (from terraform output workload_identity_provider)"
echo "  GCP_CI_SA_EMAIL       = (from terraform output ci_sa_email)"
echo "  GCP_REGISTRY          = (from terraform output registry_url)"
echo "  GCP_VM_NAME           = (from terraform output vm_instance_name)"
echo "  GCP_VM_ZONE           = $REGION-a"
echo "  GCP_STAGING_VM_NAME   = (staging terraform output vm_instance_name)"
echo "  GCP_DEPLOY_SSH_KEY    = (private key from step 6 above)"
echo "  PROD_DOMAIN           = app.clearsettle.in"
echo "  STAGING_DOMAIN        = staging.clearsettle.in"
echo ""
echo "=== Bootstrap complete ==="
