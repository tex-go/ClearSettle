#!/usr/bin/env bash
# ============================================================================
# rollback.sh — Instant rollback to any previous image tag
#
# Usage:
#   ./infra/scripts/rollback.sh prod                    # list recent tags
#   ./infra/scripts/rollback.sh prod <git-sha>          # rollback to sha
# ============================================================================
set -euo pipefail

ENV="${1:-prod}"
TARGET_TAG="${2:-}"
VM_NAME="${GCP_VM_NAME:-}"
VM_ZONE="${GCP_VM_ZONE:-asia-south1-a}"
REGISTRY="${GCP_REGISTRY:-}"
REGION="${REGISTRY%%/*}"

if [ -z "$VM_NAME" ] || [ -z "$REGISTRY" ]; then
  echo "Set GCP_VM_NAME and GCP_REGISTRY env vars"
  exit 1
fi

if [ -z "$TARGET_TAG" ]; then
  echo "Recent backend image tags in Artifact Registry:"
  gcloud artifacts docker images list "$REGISTRY/clearsettle-backend" \
    --format="table(tags,createTime)" \
    --sort-by="~createTime" \
    --limit=10 2>/dev/null || echo "(could not list — check permissions)"
  echo ""
  echo "Usage: ./infra/scripts/rollback.sh $ENV <git-sha>"
  exit 0
fi

echo "=== ROLLBACK: $ENV → $TARGET_TAG ==="
read -rp "Are you sure you want to rollback prod to $TARGET_TAG? [yes/N]: " CONFIRM
[ "$CONFIRM" = "yes" ] || { echo "Rollback cancelled."; exit 1; }

gcloud compute ssh "$VM_NAME" \
  --zone="$VM_ZONE" \
  --tunnel-through-iap \
  -- bash -s <<EOF
set -euo pipefail
cd /opt/clearsettle

# Save current tag for post-mortem
CURRENT_TAG=\$(grep "^IMAGE_TAG=" .env.prod | cut -d= -f2)
echo "Rolling back from \$CURRENT_TAG to ${TARGET_TAG}"
echo "\$CURRENT_TAG" > /opt/clearsettle/.rollback_from

gcloud auth configure-docker $REGION --quiet
sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=${TARGET_TAG}|" .env.prod

REGISTRY=$REGISTRY IMAGE_TAG=${TARGET_TAG} \
  docker compose -f docker-compose.prod.yml --env-file .env.prod pull

REGISTRY=$REGISTRY IMAGE_TAG=${TARGET_TAG} \
  docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d

echo "Rollback to ${TARGET_TAG} complete"
docker compose -f docker-compose.prod.yml ps
EOF

echo ""
echo "=== Rollback done. Previous tag was: $(cat /tmp/.rollback_from 2>/dev/null || echo 'unknown') ==="
