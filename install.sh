#!/bin/bash
# MAGNATRIX-OS Installation Script
# Quick installer for Linux/macOS systems

set -e

REPO_URL="https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git"
INSTALL_DIR="${MAGNATRIX_HOME:-/opt/magnatrix}"
PYTHON_MIN="3.10"
USER="magnatrix"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err() { echo -e "${RED}[ERR]${NC} $1"; }

check_python() {
    log_info "Checking Python version..."
    if ! command -v python3 &> /dev/null; then
        log_err "Python3 is not installed. Please install Python ${PYTHON_MIN} or higher."
        exit 1
    fi
    PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [ "$(printf '%s\n' "$PYTHON_MIN" "$PYVER" | sort -V | head -n1)" != "$PYTHON_MIN" ]; then
        log_err "Python ${PYTHON_MIN} or higher is required. Found: ${PYVER}"
        exit 1
    fi
    log_ok "Python ${PYVER} found"
}

create_user() {
    if ! id "$USER" &>/dev/null; then
        log_info "Creating system user: ${USER}"
        useradd -r -s /bin/false -d "$INSTALL_DIR" -M "$USER" 2>/dev/null || true
    else
        log_ok "User ${USER} already exists"
    fi
}

install_repo() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        log_warn "Repository already exists at ${INSTALL_DIR}. Pulling latest..."
        cd "$INSTALL_DIR"
        git pull origin main
    else
        log_info "Cloning MAGNATRIX-OS repository..."
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
    chown -R "$USER:$USER" "$INSTALL_DIR"
    log_ok "Repository installed at ${INSTALL_DIR}"
}

install_systemd() {
    if command -v systemctl &> /dev/null; then
        log_info "Installing systemd service..."
        cp "$INSTALL_DIR/magnatrix.service" /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable magnatrix.service
        log_ok "Systemd service installed. Run: systemctl start magnatrix"
    else
        log_warn "systemctl not found. Skipping systemd service installation."
    fi
}

create_dirs() {
    mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/logs"
    chown -R "$USER:$USER" "$INSTALL_DIR"
}

start_service() {
    read -p "Start MAGNATRIX-OS now? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v systemctl &> /dev/null; then
            systemctl start magnatrix
            log_ok "Service started. Dashboard: http://localhost:8080"
        else
            log_info "Starting in foreground..."
            cd "$INSTALL_DIR"
            python3 core/web_dashboard_server_native.py &
            log_ok "Dashboard: http://localhost:8080"
        fi
    fi
}

print_banner() {
    echo -e "${BLUE}"
    echo "  __  __   ___   _____   _   _   _____   _____   ____   _____   _____  ____"
    echo " |  \\/  | / _ \\ |  __ \\ | | | | /  ___| |_   _| |  _ \\ |  __ \\ |_   _|/ ___|"
    echo " | \\  / |/ /_\\ \\| |  | || | | | \\  '--.    | |   | |_) || |__) |  | |  \\  '--."
    echo " | |\\/| ||  _  || |  | || | | |  '--. \\   | |   |  _ < |  _  /   | |   '--. \\"
    echo " | |  | || | | || |__| || |_| | /\\__/ /  _| |_  | |_) || | \\ \\  _| |_ /\\__/ /"
    echo " |_|  |_||_| |_||_____/  \\___/  \\____/  |_____| |____/ |_|  \\_\\|_____|\\____/"
    echo -e "${NC}"
    echo -e "${GREEN}Private. Uncensored. Open-Source AI Operating System.${NC}"
    echo
}

main() {
    print_banner
    log_info "Starting MAGNATRIX-OS installation..."
    check_python
    create_user
    install_repo
    create_dirs
    install_systemd
    log_ok "Installation complete!"
    start_service
    echo
    log_info "Manage service: systemctl {start|stop|restart|status} magnatrix"
    log_info "Dashboard:    http://localhost:8080"
    log_info "Logs:           journalctl -u magnatrix -f"
}

main "$@"
