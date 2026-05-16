FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
# gettext provides envsubst (needed for runtime env injection)
RUN apk add --no-cache gettext

COPY --from=builder /app/dist /usr/share/nginx/html

# Template config — will be processed by entrypoint.sh at startup
COPY nginx.template.conf /etc/nginx/conf.d/default.conf.template

# Entrypoint: substitutes ${PORT} and ${API_URL} into the template, then starts nginx
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Railway sets PORT at runtime — default to 80 for local Docker Compose
EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
