# MAGNATRIX-OS Dockerfile
# ════════════════════════════════════════════════════════════════
# Multi-stage build: compile C++ HFT + Rust Crypto, then bundle Python.
#
# Build:
#   docker build -t magnatrix-os:latest .
# Run:
#   docker run -p 8080:8080 -p 8765:8765 magnatrix-os:latest
#   docker run -it --rm magnatrix-os:latest magnatrix status

# ── Stage 1: Build C++ HFT Engine ───────────────────────────────────────────
FROM python:3.12-slim AS cpp-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ cmake make && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY trading/cpp_hft_engine/ .
RUN pip install pybind11
RUN python3 -c "import pybind11; print(pybind11.get_include())" > /tmp/pybind_include.txt
RUN PYINC=$(python3 -c "import pybind11; print(pybind11.get_include())") && \
    PYHEAD=$(python3 -c "import sysconfig; print(sysconfig.get_paths()['include'])") && \
    g++ -O3 -shared -fPIC -std=c++17 \
    -I${PYHEAD} -I${PYINC} -Iinclude \
    src/order_book.cpp src/arbitrage_detector.cpp src/hft_engine.cpp src/bindings.cpp \
    -o _hft_engine.so

# ── Stage 2: Build Rust Crypto Engine ───────────────────────────────────────
FROM rust:1.82-slim AS rust-builder

WORKDIR /build
COPY security/rust_crypto_engine/ .
RUN apt-get update && apt-get install -y --no-install-recommends python3-dev && rm -rf /var/lib/apt/lists/*
RUN pip install maturin || pip install setuptools-rust
RUN cargo build --release
# .so will be in target/release/

# ── Stage 3: Final Runtime ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="MAGNATRIX-OS"
LABEL org.opencontainers.image.description="Open-Source AI Operating System"
LABEL org.opencontainers.image.version="0.9.5-alpha"

# Install runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/magnatrix-os

# Copy Python codebase
COPY . .

# Copy compiled C++ extension
COPY --from=cpp-builder /build/_hft_engine.so trading/cpp_hft_engine/

# Copy compiled Rust extension (if available)
COPY --from=rust-builder /build/target/release/*.so security/rust_crypto_engine/ 2>/dev/null || true

# Install package
RUN pip install --no-cache-dir -e .

# Expose ports
# 8080 — Dashboard HTTP server
# 8765 — WebSocket metrics stream
# 9090 — P2P mesh (optional)
EXPOSE 8080 8765 9090

# Data volume
VOLUME ["/root/.magnatrix-os"]

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import magnatrix; print('ok')" || exit 1

# Default: boot with dashboard + websocket
CMD ["python3", "-m", "magnatrix", "boot"]
