#!/bin/bash
# MAGNATRIX — One-Command Deploy ke Hostinger VPS
# Usage: ./deploy.sh [PASSWORD]
set -e

HOST="72.61.211.141"
PORT="65002"
USER="u721595593"
PASS="${1:-${HOSTINGER_SSH_PASSWORD}}"

if [ -z "$PASS" ]; then
    echo "Usage: ./deploy.sh <ssh_password>"
    echo "Atau set environment: export HOSTINGER_SSH_PASSWORD=..."
    exit 1
fi

echo "=== MAGNATRIX Deploy ke Hostinger ==="
echo "Host: $HOST:$PORT"
echo "User: $USER"

# Install sshpass jika belum ada
if ! command -v sshpass &> /dev/null; then
    echo "Installing sshpass..."
    sudo apt-get install -y sshpass 2>/dev/null || brew install sshpass 2>/dev/null || echo "Install sshpass manual: https://github.com/kevinburke/sshpass"
fi

# Deploy via SSH
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -p $PORT $USER@$HOST << 'REMOTE'
    set -e
    echo "[1] Updating code..."
    mkdir -p /opt/magnatrix
    cd /opt/magnatrix
    if [ -d .git ]; then
        git pull origin main
    else
        git clone https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git .
    fi
    
    echo "[2] Writing environment..."
    if [ ! -f .env ]; then
        echo "WARNING: .env tidak ditemukan. Buat manual dari .env.example"
    fi
    
    echo "[3] Starting Docker services..."
    docker-compose -f infrastructure/docker/docker-compose.hostinger.yml down 2>/dev/null || true
    docker-compose -f infrastructure/docker/docker-compose.hostinger.yml up --build -d
    
    echo "[4] Cleanup..."
    docker system prune -f
    
    echo "[5] Status:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "=== DEPLOY SELESAI ==="
    echo "API: http://$HOST:8080"
    echo "Mesh: http://$HOST:8081"
REMOTE

echo ""
echo "Deploy script selesai. Cek log di atas."
