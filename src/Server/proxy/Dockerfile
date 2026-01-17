# syntax=docker/dockerfile:1
FROM nginx:1.25-alpine

# Run Nginx in foreground and with minimal packages
RUN apk --no-cache add bash ca-certificates && update-ca-certificates

# Copy the Nginx configuration generated for the reverse proxy
# Expecting it to be provided at build time from the project tree
COPY ./src/Server/proxy/nginx.conf /etc/nginx/nginx.conf

# Create directories required by Nginx if they don't exist
RUN mkdir -p /var/cache/nginx /var/log/nginx /etc/nginx/conf.d \
    && chown -R nginx:nginx /var/cache/nginx /var/log/nginx

# Expose:
# - 80 (web reverse proxy -> web:8001)
# - 8081 (beacon reverse proxy -> server:2001)
EXPOSE 80 8081

# Use a non-root user for better security (optional; comment out if you need root)
USER nginx

# Healthcheck using the simple /healthz endpoint defined in nginx.conf
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/healthz || wget -qO- http://127.0.0.1:8081/healthz || exit 1

# Start Nginx in the foreground (Docker best practice)
CMD ["nginx", "-g", "daemon off;"]
