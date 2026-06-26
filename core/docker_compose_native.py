#!/usr/bin/env python3
"""
Docker Compose + Installer Builder for MAGNATRIX-OS
====================================================
Generates docker-compose.yml, install.sh, and Dockerfile programmatically.
One-command install for cross-platform deployment.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, os, platform, sys, textwrap
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ServiceConfig:
    """Docker service configuration."""
    image: str = ""
    build: Optional[Dict[str, str]] = None
    ports: List[str] = field(default_factory=list)
    volumes: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    command: str = ""
    restart: str = "unless-stopped"
    healthcheck: Optional[Dict[str, Any]] = None
    depends_on: List[str] = field(default_factory=list)
    deploy: Optional[Dict[str, Any]] = None
    networks: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.image:
            d["image"] = self.image
        if self.build:
            d["build"] = self.build
        if self.ports:
            d["ports"] = self.ports
        if self.volumes:
            d["volumes"] = self.volumes
        if self.environment:
            d["environment"] = self.environment
        if self.command:
            d["command"] = self.command
        if self.restart:
            d["restart"] = self.restart
        if self.healthcheck:
            d["healthcheck"] = self.healthcheck
        if self.depends_on:
            d["depends_on"] = self.depends_on
        if self.deploy:
            d["deploy"] = self.deploy
        if self.networks:
            d["networks"] = self.networks
        if self.labels:
            d["labels"] = self.labels
        return d


class DockerComposeBuilder:
    """Programmatically builds docker-compose.yml."""

    def __init__(self, version: str = "3.8") -> None:
        self.version = version
        self.services: Dict[str, ServiceConfig] = {}
        self.volumes: Dict[str, Any] = {}
        self.networks: Dict[str, Any] = {}

    def add_service(self, name: str, config: ServiceConfig) -> None:
        self.services[name] = config

    def add_volume(self, name: str, driver: str = "local") -> None:
        self.volumes[name] = {"driver": driver}

    def add_network(self, name: str, driver: str = "bridge") -> None:
        self.networks[name] = {"driver": driver}

    def build(self) -> str:
        compose: Dict[str, Any] = {"version": self.version}
        compose["services"] = {k: v.to_dict() for k, v in self.services.items()}
        if self.volumes:
            compose["volumes"] = self.volumes
        if self.networks:
            compose["networks"] = self.networks
        return self._to_yaml(compose)

    @staticmethod
    def _to_yaml(obj: Any, indent: int = 0) -> str:
        prefix = "  " * indent
        if isinstance(obj, dict):
            lines = []
            for k, v in obj.items():
                if isinstance(v, dict):
                    lines.append(f"{prefix}{k}:")
                    lines.append(DockerComposeBuilder._to_yaml(v, indent + 1))
                elif isinstance(v, list):
                    lines.append(f"{prefix}{k}:")
                    for item in v:
                        if isinstance(item, dict):
                            lines.append(f"{prefix}  - {list(item.keys())[0]}:")
                            sub = item[list(item.keys())[0]]
                            if isinstance(sub, dict):
                                lines.append(DockerComposeBuilder._to_yaml(sub, indent + 2))
                            else:
                                lines.append(f"{prefix}    {sub}")
                        else:
                            lines.append(f"{prefix}  - {item}")
                else:
                    lines.append(f"{prefix}{k}: {v}")
            return "\n".join(lines)
        elif isinstance(obj, list):
            return "\n".join(f"{prefix}- {item}" for item in obj)
        return str(obj)

    def write(self, path: str = "docker-compose.yml") -> None:
        with open(path, "w") as f:
            f.write(self.build())


class InstallerBuilder:
    """Generates install.sh script for cross-platform install."""

    @staticmethod
    def detect_os() -> str:
        system = platform.system().lower()
        if system == "linux":
            return "linux"
        elif system == "darwin":
            return "macos"
        elif system == "windows":
            return "windows"
        return "unknown"

    @staticmethod
    def generate() -> str:
        return textwrap.dedent("""\
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
        """)

    @staticmethod
    def write(path: str = "install.sh") -> None:
        script = InstallerBuilder.generate()
        with open(path, "w") as f:
            f.write(script)
        os.chmod(path, 0o755)


class BootstrapManager:
    """Top-level orchestrator for generating deployment files."""

    def __init__(self, repo_root: str = ".") -> None:
        self.repo_root = repo_root
        self.compose_builder = DockerComposeBuilder()
        self._setup_default_services()

    def _setup_default_services(self) -> None:
        self.compose_builder.add_network("magnatrix-net", "bridge")
        self.compose_builder.add_volume("magnatrix-data", "local")
        self.compose_builder.add_volume("magnatrix-logs", "local")

        core = ServiceConfig(
            image="magnatrix-os:latest",
            build={"context": ".", "dockerfile": "Dockerfile"},
            ports=["8080:8080"],
            volumes=[
                "magnatrix-data:/data",
                "magnatrix-logs:/logs",
            ],
            environment={
                "MAGNATRIX_ENV": "production",
                "MAGNATRIX_LOG_LEVEL": "info",
                "MAGNATRIX_PORT": "8080",
            },
            command="python magnatrix.py start --port 8080",
            restart="unless-stopped",
            healthcheck={
                "test": ["CMD", "curl", "-f", "http://localhost:8080/api/status"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "40s",
            },
            networks=["magnatrix-net"],
            labels={
                "app": "magnatrix-core",
                "tier": "core",
            },
        )
        self.compose_builder.add_service("magnatrix-core", core)

        dashboard = ServiceConfig(
            image="magnatrix-os:latest",
            ports=["8081:8081"],
            environment={
                "MAGNATRIX_DASHBOARD_PORT": "8081",
                "MAGNATRIX_CORE_HOST": "magnatrix-core",
            },
            command="python -c 'from core.dashboard_production_native import DashboardServer; DashboardServer(port=8081).start()",
            depends_on=["magnatrix-core"],
            networks=["magnatrix-net"],
            labels={"app": "magnatrix-dashboard", "tier": "frontend"},
        )
        self.compose_builder.add_service("magnatrix-dashboard", dashboard)

        logs = ServiceConfig(
            image="magnatrix-os:latest",
            volumes=["magnatrix-logs:/logs"],
            environment={"MAGNATRIX_LOG_AGGREGATOR": "true"},
            command="python -c 'import time; time.sleep(999999)'",
            depends_on=["magnatrix-core"],
            networks=["magnatrix-net"],
            labels={"app": "magnatrix-logs", "tier": "support"},
        )
        self.compose_builder.add_service("magnatrix-logs", logs)

    def generate_compose(self) -> str:
        return self.compose_builder.build()

    def generate_installer(self) -> str:
        return InstallerBuilder.generate()

    def generate_dockerfile(self) -> str:
        return textwrap.dedent("""\
            FROM python:3.11-slim

            WORKDIR /app

            # Install minimal system deps
            RUN apt-get update -qq && \\
                apt-get install -y -qq curl git && \\
                rm -rf /var/lib/apt/lists/*

            # Copy source
            COPY . /app/

            # Set environment
            ENV PYTHONUNBUFFERED=1
            ENV PYTHONDONTWRITEBYTECODE=1
            ENV MAGNATRIX_ENV=production

            # Health check
            HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
                CMD curl -f http://localhost:8080/api/status || exit 1

            EXPOSE 8080 8081

            ENTRYPOINT ["python", "magnatrix.py"]
            CMD ["start", "--port", "8080"]
        """)

    def validate(self) -> Dict[str, Any]:
        compose = self.generate_compose()
        installer = self.generate_installer()
        dockerfile = self.generate_dockerfile()
        errors = []
        if not compose.strip().startswith("version"):
            errors.append("Invalid docker-compose.yml")
        if "#!/usr/bin/env bash" not in installer:
            errors.append("Invalid install.sh")
        if "FROM" not in dockerfile:
            errors.append("Invalid Dockerfile")
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "compose_lines": len(compose.splitlines()),
            "installer_lines": len(installer.splitlines()),
            "dockerfile_lines": len(dockerfile.splitlines()),
        }

    def write_files(self, root: Optional[str] = None) -> Dict[str, str]:
        root = root or self.repo_root
        compose_path = os.path.join(root, "docker-compose.yml")
        installer_path = os.path.join(root, "install.sh")
        dockerfile_path = os.path.join(root, "Dockerfile")

        with open(compose_path, "w") as f:
            f.write(self.generate_compose())

        with open(installer_path, "w") as f:
            f.write(self.generate_installer())
        os.chmod(installer_path, 0o755)

        with open(dockerfile_path, "w") as f:
            f.write(self.generate_dockerfile())

        return {
            "docker-compose.yml": compose_path,
            "install.sh": installer_path,
            "Dockerfile": dockerfile_path,
        }
