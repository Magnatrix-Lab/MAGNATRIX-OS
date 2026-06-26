#!/usr/bin/env bash
# MAGNATRIX-OS One-Command Installer
# Cross-platform: Linux, macOS, Windows (WSL)

set -e

REPO_URL="https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git"
INSTALL_DIR="${HOME}/magnatrix-os"
DASHBOARD_URL="http://localhost:8080"

detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "macos";;
        CYGWIN*|MINGW*|MSYS*) echo "windows";;
        *)          echo "unknown";;
    esac
}

check_prerequisites() {
    echo "[1/5] Checking prerequisites..."
    OS=$(detect_os)
    echo "    OS: $OS"
    if command -v docker &> /dev/null; then
        echo "    Docker: OK"
    else
        echo "    Docker: NOT FOUND"
        return 1
    fi
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        echo "    Docker Compose: OK"
    else
        echo "    Docker Compose: NOT FOUND"
        return 1
    fi
    return 0
}

install_docker() {
    OS=$(detect_os)
    echo "[2/5] Installing Docker..."
    if [ "$OS" = "linux" ]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y -qq docker.io docker-compose
        elif command -v yum &> /dev/null; then
            sudo yum install -y -q docker docker-compose
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm docker docker-compose
        fi
    elif [ "$OS" = "macos" ]; then
        if command -v brew &> /dev/null; then
            brew install --cask docker
        else
            echo "    Please install Docker Desktop for Mac manually."
            exit 1
        fi
    elif [ "$OS" = "windows" ]; then
        echo "    Please install Docker Desktop for Windows manually."
        exit 1
    fi
    sudo systemctl start docker 2>/dev/null || true
}

clone_repo() {
    echo "[3/5] Cloning MAGNATRIX-OS repository..."
    if [ -d "$INSTALL_DIR" ]; then
        echo "    Directory exists, pulling latest..."
        cd "$INSTALL_DIR" && git pull --quiet || true
    else
        git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
    fi
}

run_compose() {
    echo "[4/5] Building and starting MAGNATRIX-OS..."
    cd "$INSTALL_DIR"
    if docker-compose version &> /dev/null; then
        docker-compose up -d --build
    else
        docker compose up -d --build
    fi
}

verify_install() {
    echo "[5/5] Verifying installation..."
    for i in {1..30}; do
        if curl -sf "$DASHBOARD_URL/api/status" &> /dev/null; then
            echo ""
            echo "=========================================="
            echo "  MAGNATRIX-OS installed successfully!"
            echo "  Dashboard: $DASHBOARD_URL"
            echo "  Install dir: $INSTALL_DIR"
            echo "=========================================="
            exit 0
        fi
        sleep 2
        echo -n "."
    done
    echo ""
    echo "  WARNING: Health check timeout. Check logs:"
    echo "    cd $INSTALL_DIR && docker-compose logs"
}

main() {
    echo "=========================================="
    echo "  MAGNATRIX-OS Installer"
    echo "=========================================="
    OS=$(detect_os)
    echo "  Detected OS: $OS"
    echo ""

    if ! check_prerequisites; then
        read -p "Docker not found. Install automatically? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker
        else
            echo "  Please install Docker and Docker Compose, then re-run."
            exit 1
        fi
    fi

    clone_repo
    run_compose
    verify_install
}

main "$@"
