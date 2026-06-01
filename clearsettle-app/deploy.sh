#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$REPO_ROOT/clearsettle-app"
COMPOSE="docker compose -f $APP_DIR/docker-compose.prod.yml --env-file $APP_DIR/.env.prod"

echo "▶ Pulling latest code..."
cd "$REPO_ROOT" && git pull origin dev

echo "▶ Rebuilding and restarting containers..."
$COMPOSE up --build -d

echo "▶ Waiting for backend to be healthy..."
timeout 60 bash -c "until $COMPOSE exec backend curl -sf http://localhost:8000/health; do sleep 3; done"

echo "▶ Running migrations..."
$COMPOSE exec backend alembic upgrade head

echo ""
echo "✓ Deployed successfully"
$COMPOSE ps
