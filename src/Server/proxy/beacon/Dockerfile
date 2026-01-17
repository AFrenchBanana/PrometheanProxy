# syntax=docker/dockerfile:1
FROM nginx:1.25-alpine

# Install minimal tools and update CA certificates
RUN apk --no-cache add bash ca-certificates && update-ca-certificates

# Copy dedicated Nginx configuration for the beacon proxy
# This config proxies external port 8081 to the internal beacon service (server:2001)
COPY ./src/Server/proxy/beacon/nginx.conf /etc/nginx/nginx.conf

# Prepare necessary directories and set permissions
RUN mkdir -p /var/cache/nginx /var/log/nginx /etc/nginx/conf.d \
    && chown -R nginx:nginx /var/cache/nginx /var/log/nginx

# Expose HTTP port for the beacon proxy
EXPOSE 8081

# Run as non-root for improved security (disable if you need root)
USER nginx

# Healthcheck against the simple /healthz endpoint served by Nginx
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8081/healthz || exit 1

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
