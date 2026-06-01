#!/bin/bash
# ssl-issue-prod.sh — Issue a REAL (non-staging) Let's Encrypt certificate.
# Run this after ssl-init.sh confirms the staging cert works.
#
# Usage:
#   sudo ./scripts/ssl-issue-prod.sh your@email.com
#
set -euo pipefail

DOMAIN="clearsettle.in"
EMAIL="${1:-}"

if [[ -z "$EMAIL" ]]; then
  echo "Usage: $0 your@email.com"
  exit 1
fi

echo "Issuing REAL Let's Encrypt certificate for $DOMAIN..."

# Stop production Nginx temporarily so port 80 is free
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true

# Start bootstrap Nginx
docker run --rm -d \
  --name cs-bootstrap-nginx \
  -p 80:80 \
  -v "$(pwd)/nginx/nginx.bootstrap.conf:/etc/nginx/nginx.conf:ro" \
  -v "/opt/clearsettle/certbot/www:/var/www/certbot" \
  nginx:1.27-alpine
sleep 3

# Issue real certificate (no --staging)
docker run --rm \
  -v "/opt/clearsettle/certbot/certs:/etc/letsencrypt" \
  -v "/opt/clearsettle/certbot/www:/var/www/certbot" \
  certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

docker stop cs-bootstrap-nginx

# Restart full production stack
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "REAL certificate issued and stack restarted."
echo "clearsettle.in should now show a green padlock."
