FROM nginx:1.27-alpine
COPY nginx.prod.conf /etc/nginx/nginx.conf
RUN nginx -t
EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
