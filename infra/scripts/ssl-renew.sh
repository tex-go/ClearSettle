#!/usr/bin/env bash
# ssl-renew.sh — Force SSL cert renewal on the VM (run from local machine via IAP)
# Usage: ./infra/scripts/ssl-renew.sh
set -euo pipefail
VM_NAME="${GCP_VM_NAME}"
VM_ZONE="${GCP_VM_ZONE:-asia-south1-a}"
DOMAIN="${PROD_DOMAIN:-app.clearsettle.in}"
EMAIL="${ALERT_EMAIL:-sudo.ranjith@gmail.com}"

gcloud compute ssh "$VM_NAME" --zone="$VM_ZONE" --tunnel-through-iap -- bash -s <<EOF
certbot certonly --webroot -w /opt/clearsettle/certbot-www \
  -d $DOMAIN -d www.$DOMAIN \
  --email $EMAIL --agree-tos --non-interactive --renew-by-default
docker compose -f /opt/clearsettle/docker-compose.prod.yml exec nginx nginx -s reload
echo "SSL renewed and nginx reloaded"
EOF
