"""
infrastructure/docker/production_dockerfile.py
===============================================
MAGNATRIX Production Docker Configuration

Dockerfile + docker-compose untuk production deployment.
Multi-stage build, health checks, resource limits.
"""

DOCKERFILE = r"""
# ============================================
# MAGNATRIX Agentic OS — Production Dockerfile
# ============================================

FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Production stage ---
FROM python:3.11-slim as production

LABEL maintainer="MAGNATRIX-OS"
LABEL version="1.0.0"
LABEL description="MAGNATRIX Agentic Operating System"

WORKDIR /app

# Copy installed dependencies dari builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy codebase
COPY . /app/

# Non-root user untuk security
RUN groupadd -r magnatrix && useradd -r -g magnatrix magnatrix
RUN chown -R magnatrix:magnatrix /app
USER magnatrix

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Expose ports
EXPOSE 8080  # API Gateway
EXPOSE 8081  # Mesh P2P
EXPOSE 8082  # Web Dashboard
EXPOSE 6379  # Redis (if bundled)

# Environment
ENV PYTHONPATH=/app
ENV MAGNATRIX_ENV=production
ENV MAGNATRIX_LOG_LEVEL=INFO

# Entry point
CMD ["python", "scripts/master_orchestrator.py"]
"""

COMPOSE = r"""
# ============================================
# MAGNATRIX Agentic OS — Production Compose
# ============================================
version: '3.8'

services:
  magnatrix-core:
    build:
      context: ..
      dockerfile: infrastructure/docker/Dockerfile
    image: magnatrix/os:latest
    container_name: magnatrix-core
    restart: unless-stopped
    ports:
      - "8080:8080"   # API Gateway
      - "8081:8081"   # P2P Mesh
      - "8082:8082"   # Dashboard
    environment:
      - MAGNATRIX_ENV=production
      - MAGNATRIX_DB_URL=postgresql://magnatrix:${DB_PASSWORD}@postgres:5432/magnatrix
      - MAGNATRIX_REDIS_URL=redis://redis:6379
      - MAGNATRIX_MESH_BOOTSTRAP=ws://magnatrix-core:8081
    volumes:
      - magnatrix-data:/app/data
      - magnatrix-logs:/app/logs
    depends_on:
      - postgres
      - redis
      - searxng
    networks:
      - magnatrix-net
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '1.0'
          memory: 2G
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # PostgreSQL dengan pgvector
  postgres:
    image: ankane/pgvector:latest
    container_name: magnatrix-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=magnatrix
      - POSTGRES_PASSWORD=${DB_PASSWORD:-magnatrix123}
      - POSTGRES_DB=magnatrix
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - magnatrix-net

  # Redis untuk cache & queue
  redis:
    image: redis:7-alpine
    container_name: magnatrix-redis
    restart: unless-stopped
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    networks:
      - magnatrix-net

  # SearXNG untuk search
  searxng:
    image: searxng/searxng:latest
    container_name: magnatrix-searxng
    restart: unless-stopped
    volumes:
      - ./searxng/settings.yml:/etc/searxng/settings.yml:ro
    ports:
      - "8083:8080"
    networks:
      - magnatrix-net

  # Optional: Prometheus monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: magnatrix-prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - magnatrix-net
    profiles:
      - monitoring

  # Optional: Grafana dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: magnatrix-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    ports:
      - "3000:3000"
    networks:
      - magnatrix-net
    profiles:
      - monitoring

volumes:
  magnatrix-data:
  magnatrix-logs:
  postgres-data:
  redis-data:
  prometheus-data:
  grafana-data:

networks:
  magnatrix-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
"""

if __name__ == "__main__":
    import os
    os.makedirs('/mnt/agents/MAGNATRIX-OS/infrastructure/docker', exist_ok=True)

    with open('/mnt/agents/MAGNATRIX-OS/infrastructure/docker/Dockerfile', 'w') as f:
        f.write(DOCKERFILE)
    print("Dockerfile written")

    with open('/mnt/agents/MAGNATRIX-OS/infrastructure/docker/docker-compose.prod.yml', 'w') as f:
        f.write(COMPOSE)
    print("docker-compose.prod.yml written")

    # Requirements file
    requirements = """
# MAGNATRIX Production Dependencies
aiohttp>=3.8.0
aiosqlite>=0.19.0
numpy>=1.24.0
cryptography>=41.0.0
asyncio-mqtt>=0.16.0
prometheus-client>=0.17.0
psycopg2-binary>=2.9.0
redis>=4.6.0
python-jose>=3.3.0
passlib>=1.7.0
httpx>=0.24.0
"""
    with open('/mnt/agents/MAGNATRIX-OS/requirements.txt', 'w') as f:
        f.write(requirements.strip())
    print("requirements.txt written")
