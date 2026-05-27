# ═══════════════════════════════════════════════════════════════════════════════
# MAGNATRIX-OS Makefile
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: help install build test start stop clean update lint

# Default target
help:
	@echo "MAGNATRIX-OS — Super AI Control Interface"
	@echo ""
	@echo "Commands:"
	@echo "  make install    Install MAGNATRIX-OS (Linux/macOS)"
	@echo "  make build      Build C++ and Rust engines"
	@echo "  make test       Run all tests"
	@echo "  make start      Start with Docker Compose"
	@echo "  make stop       Stop Docker Compose"
	@echo "  make clean      Clean build artifacts"
	@echo "  make update     Update to latest version"
	@echo "  make lint       Run linters (ruff, black)"
	@echo "  make help       Show this help"

# ── Install ────────────────────────────────────────────────────────────────────
install:
	@echo "Installing MAGNATRIX-OS..."
	bash install.sh

# ── Build ──────────────────────────────────────────────────────────────────────
build:
	@echo "Building C++ HFT Engine..."
	mkdir -p trading/cpp_hft_engine/build && cd trading/cpp_hft_engine/build && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j$$(nproc 2>/dev/null || echo 2) || echo "C++ build failed — Python fallback active"
	@echo "Building Rust Crypto Engine..."
	cd security/rust_crypto_engine && cargo build --release || echo "Rust build failed — Python fallback active"

# ── Test ───────────────────────────────────────────────────────────────────────
test:
	@echo "Running tests..."
	python tests/run_all_tests.py

# ── Docker ─────────────────────────────────────────────────────────────────────
start:
	docker compose up -d

stop:
	docker compose down

# ── Clean ──────────────────────────────────────────────────────────────────────
clean:
	@echo "Cleaning build artifacts..."
	rm -rf trading/cpp_hft_engine/build
	rm -rf security/rust_crypto_engine/target
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.so" -delete
	find . -type f -name "*.dylib" -delete

# ── Update ─────────────────────────────────────────────────────────────────────
update:
	@echo "Updating MAGNATRIX-OS..."
	git fetch origin && git reset --hard origin/main
	pip install --no-cache-dir -e ".[all]"

# ── Lint ───────────────────────────────────────────────────────────────────────
lint:
	@echo "Running linters..."
	ruff check . --output-format=text || true
	black --check --diff . || true
