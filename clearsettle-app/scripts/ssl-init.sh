#!/bin/bash
# ssl-init.sh — First-time Let's Encrypt certificate issuance.
#
# Run this ONCE on your production server before starting the full stack.
# Prerequisites:
#   - DNS: clearsettle.in → server IP (propagated, usually takes 1-10 min)
#   - Ports 80 and 443 open in firewall (ufw allow 80 && ufw allow 443)
#   - Docker and Docker Compose installed
#   - Run from: /opt/clearsettle/clearsettle-app/
#
# Usage:
#   chmod +x scripts/ssl-init.sh
#   sudo ./scripts/ssl-init.sh your@email.com
#
set -euo pipefail

DOMAIN="clearsettle.in"
EMAIL="${1:-}"

if [[ -z "$EMAIL" ]]; then
  echo "Usage: $0 your@email.com"
  exit 1
fi

echo "======================================================================"
echo " ClearSettle — SSL Bootstrap for $DOMAIN"
echo " Email: $EMAIL"
echo "======================================================================"

# ── Step 1: Create required directories ──────────────────────────────────────
echo "[1/5] Creating certbot directories..."
mkdir -p /opt/clearsettle/certbot/www
mkdir -p /opt/clearsettle/certbot/certs
mkdir -p /opt/clearsettle/uploads

# ── Step 2: Start bootstrap Nginx (HTTP only) ────────────────────────────────
echo "[2/5] Starting bootstrap Nginx (HTTP only)..."
docker run --rm -d \
  --name cs-bootstrap-nginx \
  -p 80:80 \
  -v "$(pwd)/nginx/nginx.bootstrap.conf:/etc/nginx/nginx.conf:ro" \
  -v "/opt/clearsettle/certbot/www:/var/www/certbot" \
  nginx:1.27-alpine

echo "      Waiting 5 seconds for Nginx to be ready..."
sleep 5

# Verify Nginx is up
if ! docker ps | grep -q cs-bootstrap-nginx; then
  echo "ERROR: Bootstrap Nginx failed to start."
  exit 1
fi
echo "      Bootstrap Nginx is running."

# ── Step 3: Obtain certificate via Certbot ────────────────────────────────────
echo "[3/5] Requesting Let's Encrypt certificate..."
docker run --rm \
  -v "/opt/clearsettle/certbot/certs:/etc/letsencrypt" \
  -v "/opt/clearsettle/certbot/www:/var/www/certbot" \
  certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --staging \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

# NOTE: --staging issues a test certificate (not trusted by browsers).
# Once you confirm it works, re-run with --staging removed for a real cert:
#   Remove the "--staging \" line above and run this script again.

echo "      Certificate obtained!"
echo "      NOTE: This is a STAGING certificate for testing."
echo "      To get a REAL certificate: edit ssl-init.sh, remove '--staging'"
echo "      and run: sudo ./scripts/ssl-issue-prod.sh $EMAIL"

# ── Step 4: Stop bootstrap Nginx ─────────────────────────────────────────────
echo "[4/5] Stopping bootstrap Nginx..."
docker stop cs-bootstrap-nginx

# ── Step 5: Create Docker volumes from host paths ────────────────────────────
echo "[5/5] Done! Now start the full production stack:"
echo ""
echo "   cd clearsettle-app"
echo "   cp .env.prod.example .env.prod"
echo "   # Fill in all values in .env.prod"
echo "   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d"
echo ""
echo "   After verifying everything works with the staging cert:"
echo "   sudo ./scripts/ssl-issue-prod.sh $EMAIL"
echo "======================================================================"
