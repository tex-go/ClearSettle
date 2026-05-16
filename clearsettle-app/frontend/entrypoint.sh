#!/bin/sh
set -e

export PORT="${PORT:-80}"
export API_URL="${API_URL:-http://localhost:8000}"

# Auto-detect DNS resolver from container's /etc/resolv.conf.
# Works in any environment: Docker (127.0.0.11), Railway, K8s, etc.
# Falls back to 8.8.8.8 if resolv.conf is empty or missing.
DETECTED=$(grep -m1 '^nameserver' /etc/resolv.conf 2>/dev/null | awk '{print $2}')
export NGINX_RESOLVER="${DETECTED:-8.8.8.8}"

echo "[ClearSettle] Port:     $PORT"
echo "[ClearSettle] API URL:  $API_URL"
echo "[ClearSettle] Resolver: $NGINX_RESOLVER"

envsubst '${PORT} ${API_URL} ${NGINX_RESOLVER}' \
  < /etc/nginx/conf.d/default.conf.template \
  > /etc/nginx/conf.d/default.conf

nginx -t
exec nginx -g 'daemon off;'
