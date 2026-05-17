#!/bin/sh
set -e

echo "[ClearSettle] Starting backend..."

# Run Alembic migrations only when a PostgreSQL DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
  echo "[ClearSettle] Running database migrations..."
  alembic upgrade head
  echo "[ClearSettle] Migrations complete"
else
  echo "[ClearSettle] No DATABASE_URL — running in mock-data mode"
fi

echo "[ClearSettle] Starting uvicorn on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
