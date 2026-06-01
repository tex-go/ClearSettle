#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$REPO_ROOT/clearsettle-app"
COMPOSE="docker compose -f $APP_DIR/docker-compose.prod.yml --env-file $APP_DIR/.env.prod"

echo "▶ Pulling latest code..."
cd "$REPO_ROOT" && git pull origin dev

echo "▶ Creating required host directories..."
sudo mkdir -p /opt/clearsettle/certbot/www
sudo mkdir -p /opt/clearsettle/uploads
sudo chown -R "$USER:$USER" /opt/clearsettle

echo "▶ Rebuilding and restarting containers..."
$COMPOSE up --build -d

echo "▶ Waiting for backend to be healthy..."
timeout 120 bash -c "until $COMPOSE exec -T backend python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" 2>/dev/null; do sleep 5; done"

echo "▶ Running migrations..."
$COMPOSE exec -T backend alembic upgrade head

echo ""
echo "✓ Deployed successfully"
$COMPOSE ps
