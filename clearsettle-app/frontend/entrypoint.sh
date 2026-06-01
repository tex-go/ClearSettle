#!/bin/sh
set -e

export PORT="${PORT:-80}"
export API_URL="${API_URL:-http://localhost:8000}"

echo "[ClearSettle] PORT=$PORT  API_URL=$API_URL"

envsubst '${PORT} ${API_URL}' \
  < /etc/nginx/conf.d/default.conf.template \
  > /etc/nginx/conf.d/default.conf

echo "[ClearSettle] Generated nginx config:"
cat /etc/nginx/conf.d/default.conf

nginx -t && echo "[ClearSettle] Config OK — starting nginx"
exec nginx -g 'daemon off;'
