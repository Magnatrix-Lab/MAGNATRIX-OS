# ═══════════════════════════════════════════════════════════════════════════════
# MAGNATRIX-OS — Multi-Stage Docker Build
# ═══════════════════════════════════════════════════════════════════════════════
# Build:  docker build -t magnatrix-os .
# Run:    docker run --rm -it -p 17000:17000 magnatrix-os boot
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: Build dependencies ───────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Install build tools for potential C extensions (llama.cpp, numpy, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project metadata first (for layer caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && mkdir -p magnatrix_os && touch magnatrix_os/__init__.py \
    && pip install --no-cache-dir -e ".[all]" || true

# ── Stage 2: Runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

LABEL maintainer="Magnatrix Lab <dev@magnatrix.ai>"
LABEL description="MAGNATRIX-OS — Private Uncensored Agentic AI Operating System"
LABEL version="0.9.5-alpha"

# Runtime dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 magnatrix && \
    useradd --uid 1000 --gid magnatrix --shell /bin/bash --create-home magnatrix

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MAGNATRIX_HOME=/var/lib/magnatrix
ENV MAGNATRIX_LOG_LEVEL=INFO

# Create data directories
RUN mkdir -p /var/lib/magnatrix/{models,knowledge,logs,config,repos} \
    && chown -R magnatrix:magnatrix /var/lib/magnatrix

WORKDIR /app

# Copy application code
COPY --chown=magnatrix:magnatrix . /app/

# Install magnatrix-os in editable mode (no build deps needed now)
RUN pip install --no-cache-dir -e "." || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import magnatrix; print('OK')" || exit 1

# Ports exposed by various layers
# 17000: Inter-layer Bridge Server
# 17171: P2P Rendezvous
# 17777: P2P Transport
# 18080: API Router / HTTP Gateway
EXPOSE 17000 17171 17777 18080

USER magnatrix

# Default command: show version/help
ENTRYPOINT ["python", "-m", "magnatrix"]
CMD ["--help"]

# Sub-commands available:
#   docker run magnatrix-os boot      → Boot all 15 layers
#   docker run magnatrix-os status    → Show system status
#   docker run magnatrix-os --version → Show version
