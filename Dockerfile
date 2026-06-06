# MAGNATRIX-OS Dockerfile
# Production-ready container for the uncensored AI operating system

FROM python:3.12-slim

LABEL maintainer="MAGNATRIX-Lab"
LABEL description="MAGNATRIX-OS - Private Uncensored Open-Source AI Operating System"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MAGNATRIX_HOME=/opt/magnatrix

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR $MAGNATRIX_HOME

# Copy repository
COPY . $MAGNATRIX_HOME/

# Expose dashboard port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health', timeout=5)" || exit 1

# Default command: start dashboard server
CMD ["python", "-u", "core/web_dashboard_server_native.py"]
