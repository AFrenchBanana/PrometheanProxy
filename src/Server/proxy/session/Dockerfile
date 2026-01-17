# syntax=docker/dockerfile:1

# Use official Nginx image (Alpine) which includes the stream module
FROM nginx:1.25-alpine

# Metadata
LABEL org.opencontainers.image.title="PrometheanProxy Stream Proxy" \
    org.opencontainers.image.description="Nginx (stream) proxy for raw TCP sessions: external 2001 -> server:2000" \
    org.opencontainers.image.vendor="PrometheanProxy" \
    org.opencontainers.image.version="1.0.0"

# Install minimal tools for healthcheck (netcat)
RUN apk add --no-cache netcat-openbsd

# Allow customizing worker processes via environment variable
ENV NGINX_WORKER_PROCESSES=auto

# Copy stream (TCP) configuration
# The config listens on port 2001 and forwards to server:2000 on the Docker network
COPY ./src/Server/proxy/session/nginx.conf /etc/nginx/nginx.conf

# Expose the TCP port used by the stream proxy
EXPOSE 2001/tcp

# Simple TCP healthcheck: try connecting to the local stream port
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD nc -z 127.0.0.1 2001 || exit 1

# Entrypoint: run nginx in the foreground
# Use envsubst to optionally replace worker_processes based on NGINX_WORKER_PROCESSES if desired in future
STOPSIGNAL SIGQUIT
CMD ["nginx", "-g", "daemon off;"]
