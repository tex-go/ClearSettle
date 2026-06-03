#!/bin/bash
# ClearSettle Fast Deploy Script
#
# Strategy: only rebuild backend + frontend.
# Infrastructure containers (postgres, redis, nginx, certbot) are started
# once and left running — they never change between code deploys.
#
# Typical deploy time: 60-90s  (was 600s+)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$REPO_ROOT/clearsettle-app"
COMPOSE="docker compose -f $APP_DIR/docker-compose.prod.yml --env-file $APP_DIR/.env.prod"

# ── Enable BuildKit for faster layer-cached builds ────────────────────────────
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

echo "▶ Pulling latest code..."
cd "$REPO_ROOT"
git fetch origin
git checkout main
git pull origin main

echo "▶ Creating required host directories..."
sudo mkdir -p /opt/clearsettle/certbot/www
sudo mkdir -p /opt/clearsettle/uploads
sudo chown -R "$USER:$USER" /opt/clearsettle

# ── Start infrastructure containers (only if not already running) ─────────────
# postgres, redis, nginx, certbot — pulled once, never rebuilt on code deploy
echo "▶ Starting infrastructure (postgres, redis, nginx, certbot)..."
$COMPOSE up -d --no-build postgres redis nginx certbot 2>/dev/null || true

echo "▶ Waiting for database to be ready..."
timeout 30 bash -c \
  "until $COMPOSE exec -T postgres pg_isready -U \${POSTGRES_USER:-clearsettle_user} 2>/dev/null; \
   do sleep 2; done" \
  && echo "  Database ready." \
  || echo "  Database not ready (may already be running — continuing)"

# ── Build and restart ONLY the application containers ─────────────────────────
echo "▶ Building backend + frontend images..."
$COMPOSE build --parallel backend frontend

echo "▶ Restarting backend + frontend..."
$COMPOSE up -d --no-deps backend frontend

# ── Health check ──────────────────────────────────────────────────────────────
echo "▶ Waiting for backend health check..."
ATTEMPTS=0
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [ $ATTEMPTS -ge 24 ]; then
    echo "  ERROR: backend did not become healthy after 120s"
    $COMPOSE logs --tail=30 backend
    exit 1
  fi
  echo "  attempt $ATTEMPTS/24 — waiting 5s..."
  sleep 5
done
echo "  Backend healthy in $((ATTEMPTS * 5))s"

# ── Migrations ────────────────────────────────────────────────────────────────
echo "▶ Running database migrations..."
$COMPOSE exec -T backend alembic upgrade head

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "✓ Deployed at $(date -u)"
curl -s http://localhost:8000/ | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(f'  API version : {d[\"version\"]}'); print(f'  Status      : {d[\"status\"]}')" \
  2>/dev/null || curl -s http://localhost:8000/
echo ""
$COMPOSE ps
