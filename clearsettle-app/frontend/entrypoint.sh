#!/bin/sh
set -e

export PORT="${PORT:-80}"
export API_URL="${API_URL:-http://localhost:8000}"

echo "[ClearSettle] Starting nginx on port $PORT"
echo "[ClearSettle] Proxying /api to $API_URL"

envsubst '${PORT} ${API_URL}' \
  < /etc/nginx/conf.d/default.conf.template \
  > /etc/nginx/conf.d/default.conf

nginx -t
exec nginx -g 'daemon off;'
