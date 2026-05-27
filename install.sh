#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# MAGNATRIX-OS Installer — Linux / macOS
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERR]${NC} $*" >&2; }

REPO_URL="https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git"
INSTALL_DIR="${MAGNATRIX_INSTALL_DIR:-$HOME/MAGNATRIX-OS}"
DATA_DIR="${MAGNATRIX_DATA_DIR:-$HOME/.magnatrix}"
PYTHON_MIN="3.10"

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then echo "macos"
    else echo "unknown"; fi
}

OS=$(detect_os)

check_deps() {
    log_info "Checking dependencies..."
    local missing=()
    if ! command -v python3 &>/dev/null; then missing+=("python3")
    else
        local pyver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if [[ "$(printf '%s\n' "$PYTHON_MIN" "$pyver" | sort -V | head -n1)" != "$PYTHON_MIN" ]]; then
            log_err "Python $pyver found, but >= $PYTHON_MIN required"
            missing+=("python3 (>= $PYTHON_MIN)")
        fi
    fi
    if ! command -v git &>/dev/null; then missing+=("git"); fi
    if ! command -v docker &>/dev/null; then log_warn "Docker not found. Docker mode unavailable."; fi
    if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
        log_warn "Docker Compose not found. Docker mode unavailable."
    fi
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_err "Missing dependencies: ${missing[*]}"
        if [[ "$OS" == "linux" ]]; then
            log_info "  sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv git"
        elif [[ "$OS" == "macos" ]]; then
            log_info "  brew install python git"
        fi
        exit 1
    fi
    log_ok "All required dependencies present"
}

clone_repo() {
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        log_info "Existing installation found — updating..."
        cd "$INSTALL_DIR"
        git fetch origin && git reset --hard origin/main
    else
        log_info "Cloning MAGNATRIX-OS..."
        rm -rf "$INSTALL_DIR"
        git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
    fi
    log_ok "Repository ready"
}

setup_data_dir() {
    log_info "Setting up data directory: $DATA_DIR"
    mkdir -p "$DATA_DIR"/{models,knowledge,logs,config,repos,vault}
    chmod 700 "$DATA_DIR"
    chmod 700 "$DATA_DIR/vault"
    log_ok "Data directory ready"
}

setup_python() {
    log_info "Setting up Python environment..."
    cd "$INSTALL_DIR"
    if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
    source .venv/bin/activate
    pip install --no-cache-dir --upgrade pip setuptools wheel
    pip install --no-cache-dir -e ".[all]"
    log_ok "Python environment ready"
}

build_cpp() {
    log_info "Building C++ HFT Engine..."
    cd "$INSTALL_DIR/trading/cpp_hft_engine"
    if command -v cmake &>/dev/null; then
        mkdir -p build && cd build
        cmake .. -DCMAKE_BUILD_TYPE=Release 2>/dev/null || log_warn "CMake failed — using Python fallback"
        make -j$(nproc 2>/dev/null || echo 2) 2>/dev/null || log_warn "C++ build failed — Python fallback active"
    else
        log_warn "CMake not found — C++ Python fallback active"
    fi
    log_ok "C++ engine build attempted"
}

build_rust() {
    log_info "Building Rust Crypto Engine..."
    cd "$INSTALL_DIR/security/rust_crypto_engine"
    if command -v cargo &>/dev/null; then
        cargo build --release 2>/dev/null || log_warn "Rust build failed — Python fallback active"
    else
        log_warn "Cargo not found — Rust Python fallback active"
    fi
    log_ok "Rust engine build attempted"
}

run_tests() {
    log_info "Running tests..."
    cd "$INSTALL_DIR"
    source .venv/bin/activate
    python tests/run_all_tests.py 2>/dev/null || log_warn "Some tests failed (non-blocking)"
    log_ok "Tests completed"
}

create_launcher() {
    log_info "Creating launcher..."
    local bin_dir="$HOME/.local/bin"
    mkdir -p "$bin_dir"
    cat > "$bin_dir/magnatrix" << 'LAUNCHER_EOF'
#!/bin/bash
INSTALL_DIR="${MAGNATRIX_INSTALL_DIR:-$HOME/MAGNATRIX-OS}"
DATA_DIR="${MAGNATRIX_DATA_DIR:-$HOME/.magnatrix}"
cd "$INSTALL_DIR"

case "${1:-help}" in
    boot)
        source .venv/bin/activate
        exec python magnatrix.py boot "$@"
        ;;
    docker)
        docker compose up -d
        ;;
    test)
        source .venv/bin/activate
        exec python tests/run_all_tests.py
        ;;
    stop)
        docker compose down 2>/dev/null || true
        pkill -f "magnatrix.py" 2>/dev/null || true
        ;;
    status)
        source .venv/bin/activate
        exec python magnatrix.py status
        ;;
    update)
        cd "$INSTALL_DIR"
        git fetch origin && git reset --hard origin/main
        source .venv/bin/activate
        pip install --no-cache-dir -e ".[all]"
        echo "MAGNATRIX-OS updated."
        ;;
    *)
        echo "MAGNATRIX-OS — Super AI Control Interface"
        echo "Usage: magnatrix <command>"
        echo "  boot     Start MAGNATRIX-OS"
        echo "  docker   Start with Docker Compose"
        echo "  test     Run all tests"
        echo "  stop     Stop MAGNATRIX-OS"
        echo "  status   Show layer status"
        echo "  update   Update to latest"
        ;;
esac
LAUNCHER_EOF
    chmod +x "$bin_dir/magnatrix"
    log_ok "Launcher installed: $bin_dir/magnatrix"
    if [[ ":$PATH:" != *":$bin_dir:"* ]]; then
        log_warn "$bin_dir is not in PATH"
        log_info "Add to shell profile: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
}

main() {
    echo -e "${CYAN}"
    echo "  __  __                                   _       ____   _____ ____"
    echo " |  \/  | __ _ _ __ ___  _   _ _ __   __ _| |_ ___/ ___| |_   _/ ___|"
    echo " | |\/| |/ _\' | '_ \` _ \| | | | '_ \ / _\' | __/ _ \___ \   | | \___ \\"
    echo " | |  | | (_| | | | | | | |_| | | | | (_| | ||  __/___) |  | |  ___) |"
    echo " |_|  |_|\__,_|_| |_| |_|\__,_|_| |_|\__, |\__\___|____/   |_| |____/"
    echo "                                      |___/"
    echo -e "${NC}"
    echo "MAGNATRIX-OS Installer — Private Uncensored Agentic AI OS"
    echo "============================================================"
    echo ""

    check_deps
    clone_repo
    setup_data_dir
    setup_python
    build_cpp
    build_rust
    run_tests
    create_launcher

    echo ""
    echo -e "${GREEN}MAGNATRIX-OS installed successfully!${NC}"
    echo ""
    log_info "Installation:  $INSTALL_DIR"
    log_info "Data:          $DATA_DIR"
    log_info "Launcher:      ~/.local/bin/magnatrix"
    echo ""
    log_info "Quick start:"
    log_info "  magnatrix boot     Start MAGNATRIX-OS"
    log_info "  magnatrix docker   Start with Docker"
    log_info "  magnatrix test     Run tests"
    log_info "  magnatrix help     Show commands"
    echo ""
}

main "$@"
