#!/usr/bin/env python3
"""
Auto-Deployment Module for MAGNATRIX-OS
Docker, docker-compose, install script, auto-updater engine.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DeployConfig:
    """Deployment configuration."""
    app_name: str = "magnatrix-os"
    version: str = "1.0.0"
    port: int = 8080
    host: str = "0.0.0.0"
    python_version: str = "3.12"
    workers: int = 4
    enable_ssl: bool = False
    ssl_cert: str = ""
    ssl_key: str = ""
    data_dir: str = "./data"
    log_dir: str = "./logs"
    env: Dict[str, str] = field(default_factory=dict)


class DockerGenerator:
    """Generate Docker deployment files."""

    def __init__(self, config: DeployConfig) -> None:
        self.config = config

    def generate_dockerfile(self) -> str:
        return f"""FROM python:{self.config.python_version}-slim

LABEL maintainer="MAGNATRIX-OS <dev@magnatrix.io>"
LABEL version="{self.config.version}"
LABEL description="MAGNATRIX-OS — Private AI Operating System"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# Copy source code
COPY . /app/

# Set environment
ENV PYTHONPATH=/app
ENV MAGNATRIX_DATA_DIR=/app/data
ENV MAGNATRIX_LOG_DIR=/app/logs
ENV MAGNATRIX_PORT={self.config.port}
ENV MAGNATRIX_HOST={self.config.host}

# Create data directories
RUN mkdir -p /app/data /app/logs

# Expose port
EXPOSE {self.config.port}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:{self.config.port}/api/health || exit 1

# Default: run the web dashboard server
CMD ["python3", "-u", "core/web_dashboard_server_native.py"]
"""

    def generate_dockerignore(self) -> str:
        return """# Git
.git
.gitignore

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
dist/
build/

# Data & logs (mounted as volumes)
data/
logs/
doc_store/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Tests
tests/
.pytest_cache/
"""

    def generate_docker_compose(self) -> str:
        env_list = []
        for k, v in self.config.env.items():
            env_list.append(f"      - {k}={v}")
        env_str = "\n".join(env_list) if env_list else "      - MAGNATRIX_ENV=production"
        return f"""version: "3.8"

services:
  magnatrix:
    build: .
    image: magnatrix-os:{self.config.version}
    container_name: {self.config.app_name}
    ports:
      - "{self.config.port}:{self.config.port}"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
{env_str}
    restart: unless-stopped
    networks:
      - magnatrix-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{self.config.port}/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # Optional: Ollama sidecar for local LLM
  ollama:
    image: ollama/ollama:latest
    container_name: magnatrix-ollama
    volumes:
      - ollama-data:/root/.ollama
    ports:
      - "11434:11434"
    restart: unless-stopped
    networks:
      - magnatrix-net
    profiles:
      - with-llm

volumes:
  ollama-data:

networks:
  magnatrix-net:
    driver: bridge
"""

    def generate_nginx_conf(self) -> str:
        return """server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
"""

    def save_all(self, output_dir: str) -> Dict[str, str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        files = {
            "Dockerfile": self.generate_dockerfile(),
            ".dockerignore": self.generate_dockerignore(),
            "docker-compose.yml": self.generate_docker_compose(),
            "nginx.conf": self.generate_nginx_conf(),
        }
        for name, content in files.items():
            (out / name).write_text(content, encoding="utf-8")
        return {k: str(out / k) for k in files}


class InstallerGenerator:
    """Generate one-command installer scripts."""

    def __init__(self, config: DeployConfig) -> None:
        self.config = config

    def generate_bash_installer(self) -> str:
        return f"""#!/bin/bash
# MAGNATRIX-OS One-Command Installer
# Usage: curl -sSL https://magnatrix.io/install.sh | bash

set -e

APP_NAME="{self.config.app_name}"
VERSION="{self.config.version}"
INSTALL_DIR="$HOME/.magnatrix"
PORT="{self.config.port}"
REPO_URL="https://github.com/Magnatrix-Lab/MAGNATRIX-OS"

echo "========================================"
echo "  MAGNATRIX-OS Installer"
echo "  Version: $VERSION"
echo "========================================"

# Check dependencies
command -v python3 >/dev/null 2>&1 || {{ echo "Error: python3 required"; exit 1; }}
command -v git >/dev/null 2>&1 || {{ echo "Error: git required"; exit 1; }}

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{{sys.version_info.major}}.{{sys.version_info.minor}}")')
if [ "$(printf '%s\n' "3.10" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.10" ]; then
    echo "Error: Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi

# Create install directory
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Clone or update repo
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "[+] Updating existing installation..."
    git pull origin main
else
    echo "[+] Cloning MAGNATRIX-OS..."
    git clone --depth 1 "$REPO_URL" .
fi

# Install Python dependencies (if any requirements.txt exists)
if [ -f "requirements.txt" ]; then
    echo "[+] Installing Python dependencies..."
    python3 -m pip install -r requirements.txt
fi

# Create data directories
mkdir -p data logs

# Create launcher script
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"
python3 -u core/web_dashboard_server_native.py &
PID=$!
echo $PID > .pid
wait $PID
EOF
chmod +x start.sh

cat > stop.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [ -f .pid ]; then
    kill $(cat .pid) 2>/dev/null || true
    rm .pid
    echo "MAGNATRIX-OS stopped"
else
    echo "Not running"
fi
EOF
chmod +x stop.sh

echo ""
echo "========================================"
echo "  Installation complete!"
echo "========================================"
echo "  Directory: $INSTALL_DIR"
echo "  Start:   ./start.sh"
echo "  Stop:    ./stop.sh"
echo "  Dashboard: http://localhost:$PORT"
echo "========================================"
"""

    def generate_powershell_installer(self) -> str:
        return """# MAGNATRIX-OS Windows Installer
# Usage: irm https://magnatrix.io/install.ps1 | iex

$APP_NAME = "magnatrix-os"
$VERSION = "1.0.0"
$INSTALL_DIR = "$env:USERPROFILE\\.magnatrix"
$PORT = 8080
$REPO_URL = "https://github.com/Magnatrix-Lab/MAGNATRIX-OS"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MAGNATRIX-OS Installer" -ForegroundColor Cyan
Write-Host "  Version: $VERSION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check Python
$python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { Write-Error "Python 3 is required"; exit 1 }

# Check Git
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) { Write-Error "Git is required"; exit 1 }

# Create directory
New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
Set-Location $INSTALL_DIR

# Clone or update
if (Test-Path "$INSTALL_DIR\\.git") {
    Write-Host "[+] Updating existing installation..."
    git pull origin main
} else {
    Write-Host "[+] Cloning MAGNATRIX-OS..."
    git clone --depth 1 $REPO_URL .
}

# Create data dirs
New-Item -ItemType Directory -Force -Path "data", "logs" | Out-Null

# Create launcher
$startScript = @'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = $dir
Start-Process python3 -ArgumentList "-u", "$dir\\core\\web_dashboard_server_native.py" -WindowStyle Hidden -RedirectStandardOutput "$dir\\logs\\stdout.log" -RedirectStandardError "$dir\\logs\\stderr.log"
'@
$startScript | Out-File -Encoding UTF8 "start.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "  Directory: $INSTALL_DIR" -ForegroundColor Green
Write-Host "  Start:   .\\start.ps1" -ForegroundColor Green
Write-Host "  Dashboard: http://localhost:$PORT" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
"""

    def save_all(self, output_dir: str) -> Dict[str, str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        files = {
            "install.sh": self.generate_bash_installer(),
            "install.ps1": self.generate_powershell_installer(),
        }
        for name, content in files.items():
            path = out / name
            path.write_text(content, encoding="utf-8")
            if name.endswith(".sh"):
                os.chmod(path, 0o755)
        return {k: str(out / k) for k in files}


class AutoUpdater:
    """Auto-update engine for MAGNATRIX-OS."""

    def __init__(self, repo_url: str = "https://github.com/Magnatrix-Lab/MAGNATRIX-OS", 
                 check_interval: int = 3600) -> None:
        self.repo_url = repo_url
        self.check_interval = check_interval
        self._current_version = "1.0.0"
        self._latest_version: Optional[str] = None
        self._update_available = False

    def check_update(self) -> Dict[str, Any]:
        """Check if a new version is available via GitHub API."""
        try:
            api_url = self.repo_url.replace("github.com", "api.github.com/repos") + "/releases/latest"
            req = urllib.request.Request(api_url, headers={"User-Agent": "MAGNATRIX-OS-Updater"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latest = data.get("tag_name", "")
                self._latest_version = latest
                self._update_available = latest != self._current_version and latest != ""
                return {
                    "current": self._current_version,
                    "latest": latest,
                    "update_available": self._update_available,
                    "published_at": data.get("published_at", ""),
                    "body": data.get("body", "")[:500],
                }
        except Exception as e:
            return {
                "current": self._current_version,
                "latest": None,
                "update_available": False,
                "error": str(e),
            }

    def apply_update(self, install_dir: str) -> Dict[str, Any]:
        """Apply update via git pull."""
        try:
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=install_dir, capture_output=True, text=True, timeout=120,
            )
            success = result.returncode == 0
            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "needs_restart": True,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def download_release(self, version: str, output_dir: str) -> Dict[str, Any]:
        """Download a specific release zip."""
        url = f"{self.repo_url}/releases/download/{version}/magnatrix-os-{version}.zip"
        try:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            zip_path = out / f"magnatrix-{version}.zip"
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(out / f"magnatrix-{version}")
            return {"success": True, "zip_path": str(zip_path), "extracted_to": str(out / f"magnatrix-{version}")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_version": self._current_version,
            "latest_version": self._latest_version,
            "update_available": self._update_available,
            "check_interval": self.check_interval,
            "repo_url": self.repo_url,
        }


class AutoDeploymentManager:
    """Unified deployment manager."""

    def __init__(self, repo_root: Optional[str] = None) -> None:
        self.root = Path(repo_root) if repo_root else Path.cwd()
        self.config = DeployConfig()
        self.docker = DockerGenerator(self.config)
        self.installer = InstallerGenerator(self.config)
        self.updater = AutoUpdater()

    def generate_all(self, output_dir: Optional[str] = None) -> Dict[str, Any]:
        out = Path(output_dir) if output_dir else self.root / "deploy"
        docker_files = self.docker.save_all(out)
        installer_files = self.installer.save_all(out / "installers")
        return {
            "output_dir": str(out),
            "docker": docker_files,
            "installers": installer_files,
        }

    def check_update(self) -> Dict[str, Any]:
        return self.updater.check_update()

    def apply_update(self) -> Dict[str, Any]:
        return self.updater.apply_update(str(self.root))

    def stats(self) -> Dict[str, Any]:
        return {
            "config": {
                "app_name": self.config.app_name,
                "version": self.config.version,
                "port": self.config.port,
            },
            "updater": self.updater.get_status(),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Auto-Deployment Module Demo ===\n")
    manager = AutoDeploymentManager()
    result = manager.generate_all("/tmp/magnatrix-deploy")
    print(f"Generated to: {result['output_dir']}")
    print(f"\nDocker files:")
    for name, path in result["docker"].items():
        print(f"  {name}: {path}")
    print(f"\nInstaller files:")
    for name, path in result["installers"].items():
        print(f"  {name}: {path}")
    print(f"\nStats: {manager.stats()}")
    print(f"\nUpdate check: {manager.check_update()}")


if __name__ == "__main__":
    _demo()
