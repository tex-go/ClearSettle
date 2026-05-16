#!/bin/sh
set -e

export PORT="${PORT:-80}"
export API_URL="${API_URL:-http://localhost:8000}"
# 127.0.0.11 = Docker embedded DNS; 8.8.8.8 = public DNS for Railway
export NGINX_RESOLVER="${NGINX_RESOLVER:-8.8.8.8}"

echo "[ClearSettle] Starting nginx on port $PORT"
echo "[ClearSettle] Proxying /api to $API_URL"
echo "[ClearSettle] DNS resolver: $NGINX_RESOLVER"

envsubst '${PORT} ${API_URL} ${NGINX_RESOLVER}' \
  < /etc/nginx/conf.d/default.conf.template \
  > /etc/nginx/conf.d/default.conf

nginx -t
exec nginx -g 'daemon off;'
