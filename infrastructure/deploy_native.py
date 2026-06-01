#!/usr/bin/env python3
"""
infrastructure/deploy_native.py — MAGNATRIX-OS Deployment Orchestrator

Docker, systemd, K8s deployment. Pure Python, stdlib only.

Features: compose generation, service units, health checks, rolling updates,
backups, config templating, secret injection, log aggregation.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Tuple


class DeployError(Exception):
    pass


@dataclass
class DeployConfig:
    environment: str = "dev"
    docker_compose_file: str = "docker-compose.yml"
    systemd_dir: str = "/etc/systemd/system"
    k8s_dir: str = "k8s/"
    backup_dir: str = "backups/"
    log_dir: str = "logs/"
    registry: str = "localhost:5000"
    image_tag: str = "latest"


class ConfigTemplater:
    """Jinja2-like templating using Python string.Template."""

    @staticmethod
    def render(template: str, variables: Dict[str, Any]) -> str:
        return Template(template).substitute(variables)

    @staticmethod
    def render_file(template_path: str, output_path: str, variables: Dict[str, Any]) -> None:
        with open(template_path) as f:
            template = f.read()
        rendered = ConfigTemplater.render(template, variables)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(rendered)


class HealthChecker:
    """Post-deployment health checks."""

    @staticmethod
    def check_http(url: str, timeout: float = 5.0) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout):
                return True
        except Exception:
            return False

    @staticmethod
    def check_tcp(host: str, port: int, timeout: float = 5.0) -> bool:
        import socket
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    @staticmethod
    def check_process(pid_file: str) -> bool:
        if not os.path.exists(pid_file):
            return False
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except Exception:
            return False


class BackupManager:
    """Pre-deployment backup."""

    @staticmethod
    def create_backup(source_dirs: List[str], output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with tarfile.open(output_path, "w:gz") as tar:
            for d in source_dirs:
                if os.path.exists(d):
                    tar.add(d, arcname=os.path.basename(d))
        return output_path

    @staticmethod
    def restore_backup(backup_path: str, target_dir: str) -> None:
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(target_dir)


class SecretManager:
    """Secret injection from env vars or files."""

    @staticmethod
    def inject(secrets: Dict[str, str], target_file: str) -> None:
        with open(target_file, "w") as f:
            for key, value in secrets.items():
                f.write(f"{key}={value}\n")

    @staticmethod
    def load_from_env(prefix: str = "MAGNATRIX_") -> Dict[str, str]:
        return {k: v for k, v in os.environ.items() if k.startswith(prefix)}


class DockerDeployer:
    """Docker deployment management."""

    def __init__(self, config: DeployConfig):
        self.config = config
        self._services: Dict[str, Dict[str, Any]] = {}

    def add_service(self, name: str, image: str, ports: List[str], env: Dict[str, str], depends_on: List[str] = None) -> None:
        self._services[name] = {
            "image": image,
            "ports": ports,
            "environment": env,
            "depends_on": depends_on or [],
            "restart": "unless-stopped",
        }

    def generate_compose(self) -> str:
        compose = {"version": "3.8", "services": {}}
        for name, svc in self._services.items():
            compose["services"][name] = {
                "image": svc["image"],
                "ports": svc["ports"],
                "environment": svc["environment"],
                "restart": svc["restart"],
            }
            if svc["depends_on"]:
                compose["services"][name]["depends_on"] = svc["depends_on"]
        return json.dumps(compose, indent=2)

    def write_compose(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.generate_compose())

    def build(self, service: str) -> None:
        cmd = ["docker", "build", "-t", f"{self.config.registry}/{service}:{self.config.image_tag}", "."]
        subprocess.run(cmd, capture_output=True)

    def up(self, path: str) -> None:
        subprocess.run(["docker-compose", "-f", path, "up", "-d"], capture_output=True)

    def down(self, path: str) -> None:
        subprocess.run(["docker-compose", "-f", path, "down"], capture_output=True)

    def health_check(self) -> Dict[str, bool]:
        return {name: HealthChecker.check_tcp("localhost", int(ports[0].split(":")[0])) for name, svc in self._services.items() for ports in [svc["ports"]]}


class SystemdDeployer:
    """systemd service management."""

    def __init__(self, config: DeployConfig):
        self.config = config

    def generate_unit(self, name: str, exec_start: str, description: str, after: List[str] = None) -> str:
        after_clause = " ".join(after) if after else "network.target"
        return f"""[Unit]
Description={description}
After={after_clause}

[Service]
Type=simple
ExecStart={exec_start}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

    def write_unit(self, name: str, content: str) -> str:
        path = os.path.join(self.config.systemd_dir, f"magnatrix-{name}.service")
        os.makedirs(self.config.systemd_dir, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return path

    def start(self, name: str) -> None:
        subprocess.run(["systemctl", "start", f"magnatrix-{name}"], capture_output=True)

    def stop(self, name: str) -> None:
        subprocess.run(["systemctl", "stop", f"magnatrix-{name}"], capture_output=True)

    def enable(self, name: str) -> None:
        subprocess.run(["systemctl", "enable", f"magnatrix-{name}"], capture_output=True)

    def disable(self, name: str) -> None:
        subprocess.run(["systemctl", "disable", f"magnatrix-{name}"], capture_output=True)


class K8sDeployer:
    """Kubernetes manifest generator."""

    def __init__(self, config: DeployConfig):
        self.config = config

    def generate_deployment(self, name: str, image: str, replicas: int = 1, ports: List[int] = None) -> str:
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": name},
            "spec": {
                "replicas": replicas,
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {
                        "containers": [{
                            "name": name,
                            "image": image,
                            "ports": [{"containerPort": p} for p in (ports or [8080])],
                        }]
                    }
                }
            }
        }
        return json.dumps(deployment, indent=2)

    def generate_service(self, name: str, ports: List[Tuple[int, int]]) -> str:
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": name},
            "spec": {
                "selector": {"app": name},
                "ports": [{"port": p[0], "targetPort": p[1]} for p in ports],
            }
        }
        return json.dumps(service, indent=2)

    def write_manifest(self, name: str, content: str) -> str:
        path = os.path.join(self.config.k8s_dir, f"{name}.yaml")
        os.makedirs(self.config.k8s_dir, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return path


class RollingUpdater:
    """Rolling update with zero downtime."""

    def __init__(self, docker: DockerDeployer):
        self.docker = docker

    def update(self, service: str, new_image: str) -> bool:
        # Pull new image
        result = subprocess.run(["docker", "pull", new_image], capture_output=True)
        if result.returncode != 0:
            return False

        # Update service
        self.docker._services[service]["image"] = new_image
        compose_path = self.docker.config.docker_compose_file
        self.docker.write_compose(compose_path)

        # Rolling restart
        subprocess.run(["docker-compose", "-f", compose_path, "up", "-d", "--no-deps", "--scale", f"{service}=2", service], capture_output=True)
        time.sleep(5)
        subprocess.run(["docker-compose", "-f", compose_path, "up", "-d", "--no-deps", "--scale", f"{service}=1", service], capture_output=True)

        # Health check
        return HealthChecker.check_tcp("localhost", 8080)


class LogAggregator:
    """Collect logs from all deployed services."""

    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def collect(self, service: str) -> str:
        log_path = os.path.join(self.log_dir, f"{service}.log")
        result = subprocess.run(["docker", "logs", service], capture_output=True, text=True)
        with open(log_path, "w") as f:
            f.write(result.stdout)
        return log_path


class DeployOrchestrator:
    """Main deployment orchestrator."""

    def __init__(self, config: Optional[DeployConfig] = None):
        self.config = config or DeployConfig()
        self.docker = DockerDeployer(self.config)
        self.systemd = SystemdDeployer(self.config)
        self.k8s = K8sDeployer(self.config)
        self.rolling = RollingUpdater(self.docker)
        self.backup = BackupManager()
        self.secrets = SecretManager()
        self.logs = LogAggregator(self.config.log_dir)

    def deploy_all(self, deployment_type: str = "docker") -> Dict[str, Any]:
        results = {}

        # Backup first
        backup_path = os.path.join(self.config.backup_dir, f"backup_{int(time.time())}.tar.gz")
        self.backup.create_backup(["config/", "data/"], backup_path)
        results["backup"] = backup_path

        # Inject secrets
        secrets = self.secrets.load_from_env()
        if secrets:
            self.secrets.inject(secrets, ".env")

        if deployment_type == "docker":
            compose_path = self.config.docker_compose_file
            self.docker.write_compose(compose_path)
            results["compose_file"] = compose_path

        elif deployment_type == "systemd":
            for layer in ["kernel", "runtime", "ai", "trading", "security"]:
                unit = self.systemd.generate_unit(layer, f"python -m {layer}", f"MAGNATRIX {layer}")
                path = self.systemd.write_unit(layer, unit)
                self.systemd.enable(layer)
                self.systemd.start(layer)
                results[f"systemd_{layer}"] = path

        elif deployment_type == "k8s":
            for service in ["api", "ai", "trading"]:
                manifest = self.k8s.generate_deployment(service, f"magnatrix/{service}")
                path = self.k8s.write_manifest(f"{service}-deployment", manifest)
                results[f"k8s_{service}"] = path

        return results

    def health_check_all(self) -> Dict[str, bool]:
        return self.docker.health_check()

    def rollback(self, backup_path: str) -> None:
        self.backup.restore_backup(backup_path, ".")


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Deploy Orchestrator — Self-Test")
    print("=" * 60)

    # Test 1: ConfigTemplater
    print("\n[1] ConfigTemplater")
    t = ConfigTemplater()
    result = t.render("Hello $name!", {"name": "MAGNATRIX"})
    assert result == "Hello MAGNATRIX!"
    print("  OK")

    # Test 2: SecretManager
    print("\n[2] SecretManager")
    s = SecretManager()
    secrets = {"API_KEY": "secret123"}
    s.inject(secrets, "/tmp/test_secrets.env")
    with open("/tmp/test_secrets.env") as f:
        content = f.read()
    assert "API_KEY=secret123" in content
    print("  OK")

    # Test 3: BackupManager
    print("\n[3] BackupManager")
    b = BackupManager()
    os.makedirs("/tmp/test_src", exist_ok=True)
    with open("/tmp/test_src/file.txt", "w") as f:
        f.write("test")
    path = b.create_backup(["/tmp/test_src"], "/tmp/test_backup.tar.gz")
    assert os.path.exists(path)
    print("  OK")

    # Test 4: DockerDeployer
    print("\n[4] DockerDeployer")
    d = DockerDeployer(DeployConfig())
    d.add_service("api", "magnatrix/api", ["8080:8080"], {"ENV": "dev"})
    d.add_service("ai", "magnatrix/ai", ["8081:8081"], {"ENV": "dev"}, depends_on=["api"])
    compose = d.generate_compose()
    assert "api" in compose
    assert "ai" in compose
    print("  OK")

    # Test 5: SystemdDeployer
    print("\n[5] SystemdDeployer")
    sd = SystemdDeployer(DeployConfig(systemd_dir="/tmp/systemd"))
    unit = sd.generate_unit("kernel", "python -m kernel", "MAGNATRIX Kernel")
    assert "kernel" in unit
    print("  OK")

    # Test 6: K8sDeployer
    print("\n[6] K8sDeployer")
    k8s = K8sDeployer(DeployConfig(k8s_dir="/tmp/k8s"))
    manifest = k8s.generate_deployment("api", "magnatrix/api", replicas=2)
    assert "replicas" in manifest
    print("  OK")

    # Test 7: DeployOrchestrator
    print("\n[7] DeployOrchestrator")
    orch = DeployOrchestrator(DeployConfig(backup_dir="/tmp/backups", log_dir="/tmp/logs"))
    results = orch.deploy_all("docker")
    assert "compose_file" in results
    print("  OK")

    print("\n" + "=" * 60)
    print("All self-tests passed")
    print("=" * 60)
