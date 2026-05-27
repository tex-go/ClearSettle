#!/usr/bin/env bash
# ============================================================================
# deploy.sh — Manual production deploy helper
# Usage: ./infra/scripts/deploy.sh <git-sha>
#        ./infra/scripts/deploy.sh latest
# ============================================================================
set -euo pipefail

IMAGE_TAG="${1:-latest}"
VM_NAME="${GCP_VM_NAME:-}"
VM_ZONE="${GCP_VM_ZONE:-asia-south1-a}"
REGISTRY="${GCP_REGISTRY:-}"

if [ -z "$VM_NAME" ] || [ -z "$REGISTRY" ]; then
  echo "Set GCP_VM_NAME and GCP_REGISTRY env vars or export them"
  exit 1
fi

echo "=== Manual deploy: IMAGE_TAG=$IMAGE_TAG ==="

gcloud compute ssh "$VM_NAME" \
  --zone="$VM_ZONE" \
  --tunnel-through-iap \
  -- bash -s <<EOF
set -euo pipefail
cd /opt/clearsettle

gcloud auth configure-docker ${REGISTRY%%/*} --quiet
sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=${IMAGE_TAG}|" .env.prod

REGISTRY=$REGISTRY IMAGE_TAG=$IMAGE_TAG \
  docker compose -f docker-compose.prod.yml --env-file .env.prod pull

REGISTRY=$REGISTRY IMAGE_TAG=$IMAGE_TAG \
  docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d --no-deps backend

# Wait for backend health
for i in \$(seq 1 30); do
  STATUS=\$(docker inspect --format='{{.State.Health.Status}}' \
    clearsettle-backend-prod 2>/dev/null || echo "starting")
  [ "\$STATUS" = "healthy" ] && break
  [ \$i -eq 30 ] && { echo "Backend health check FAILED"; exit 1; }
  sleep 2
done

REGISTRY=$REGISTRY IMAGE_TAG=$IMAGE_TAG \
  docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d --no-deps frontend nginx

docker image prune -f --filter "until=168h"
echo "Deploy $IMAGE_TAG complete"
docker compose -f docker-compose.prod.yml ps
EOF
