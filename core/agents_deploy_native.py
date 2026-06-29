"""Agents Deploy - Cloud deployment orchestrator for ADK agents."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DeploymentConfig:
    config_id: str
    target: str = "cloud_run"  # cloud_run, gke, agent_runtime
    agent_name: str = ""
    region: str = "us-central1"
    project_id: str = ""
    env_vars: Dict[str, str] = field(default_factory=dict)
    secrets: List[str] = field(default_factory=list)
    scaling: Dict[str, int] = field(default_factory=dict)
    status: str = "pending"

    def to_dict(self) -> Dict:
        return {
            "config_id": self.config_id,
            "target": self.target,
            "agent_name": self.agent_name,
            "region": self.region,
            "project_id": self.project_id,
            "env_vars": self.env_vars,
            "secrets": self.secrets,
            "scaling": self.scaling,
            "status": self.status,
        }


@dataclass
class DeploymentRecord:
    deployment_id: str
    config_id: str
    status: str = "pending"  # pending, deploying, active, failed, stopped
    url: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "deployment_id": self.deployment_id,
            "config_id": self.config_id,
            "status": self.status,
            "url": self.url,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "logs": self.logs,
        }


class AgentsDeploy:
    """Cloud deployment orchestrator for ADK agents (Cloud Run, GKE, Agent Runtime)."""

    SUPPORTED_TARGETS = ["cloud_run", "gke", "agent_runtime"]

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "agents_deploy"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.configs: Dict[str, DeploymentConfig] = {}
        self.deployments: Dict[str, DeploymentRecord] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for c in data.get("configs", []):
                    self.configs[c["config_id"]] = DeploymentConfig(**c)
                for d in data.get("deployments", []):
                    self.deployments[d["deployment_id"]] = DeploymentRecord(**d)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "configs": [c.to_dict() for c in self.configs.values()],
            "deployments": [d.to_dict() for d in self.deployments.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def create_config(self, agent_name: str, target: str = "cloud_run", region: str = "us-central1", project_id: str = "") -> DeploymentConfig:
        """Create deployment configuration."""
        if target not in self.SUPPORTED_TARGETS:
            raise ValueError(f"Target {target} not supported. Choose from {self.SUPPORTED_TARGETS}")
        config_id = f"cfg_{agent_name}_{target}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
        config = DeploymentConfig(
            config_id=config_id,
            target=target,
            agent_name=agent_name,
            region=region,
            project_id=project_id,
            scaling={"min_instances": 1, "max_instances": 10},
        )
        self.configs[config_id] = config
        self._save_state()
        return config

    def deploy(self, config_id: str) -> DeploymentRecord:
        """Simulate deploying agent to cloud."""
        if config_id not in self.configs:
            raise ValueError(f"Config {config_id} not found")
        config = self.configs[config_id]
        deployment_id = f"deploy_{config_id}_{int(time.time())}"

        record = DeploymentRecord(
            deployment_id=deployment_id,
            config_id=config_id,
            status="deploying",
            started_at=time.time(),
            logs=[f"[{time.time()}] Starting deployment to {config.target}..."],
        )

        # Simulate deployment steps
        record.logs.append(f"[{time.time()}] Building container image...")
        record.logs.append(f"[{time.time()}] Pushing to {config.region}...")
        record.logs.append(f"[{time.time()}] Configuring service {config.agent_name}...")
        record.url = f"https://{config.agent_name}-{hashlib.md5(deployment_id.encode()).hexdigest()[:8]}-uc.a.run.app"
        record.status = "active"
        record.completed_at = time.time()
        record.logs.append(f"[{time.time()}] Deployment complete. URL: {record.url}")

        self.deployments[deployment_id] = record
        config.status = "deployed"
        self._save_state()
        return record

    def stop_deployment(self, deployment_id: str) -> DeploymentRecord:
        """Stop an active deployment."""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment {deployment_id} not found")
        record = self.deployments[deployment_id]
        record.status = "stopped"
        record.logs.append(f"[{time.time()}] Deployment stopped.")
        self._save_state()
        return record

    def get_deployment_status(self, deployment_id: str) -> Dict:
        if deployment_id not in self.deployments:
            return {"status": "unknown", "deployment_id": deployment_id}
        record = self.deployments[deployment_id]
        return {
            "deployment_id": deployment_id,
            "status": record.status,
            "url": record.url,
            "duration_sec": round(record.completed_at - record.started_at, 2) if record.completed_at else None,
        }

    def add_secret(self, config_id: str, secret_name: str) -> DeploymentConfig:
        """Add secret to deployment config."""
        if config_id not in self.configs:
            raise ValueError(f"Config {config_id} not found")
        config = self.configs[config_id]
        if secret_name not in config.secrets:
            config.secrets.append(secret_name)
        self._save_state()
        return config

    def set_env_var(self, config_id: str, key: str, value: str) -> DeploymentConfig:
        """Set environment variable for deployment."""
        if config_id not in self.configs:
            raise ValueError(f"Config {config_id} not found")
        config = self.configs[config_id]
        config.env_vars[key] = value
        self._save_state()
        return config

    def generate_cicd_config(self, config_id: str) -> str:
        """Generate CI/CD configuration for deployment."""
        if config_id not in self.configs:
            raise ValueError(f"Config {config_id} not found")
        config = self.configs[config_id]
        return f"""name: Deploy {config.agent_name}
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to {config.target}
        run: |
          gcloud run deploy {config.agent_name} --region {config.region}
"""

    def get_stats(self) -> Dict:
        active = sum(1 for d in self.deployments.values() if d.status == "active")
        return {
            "configs_total": len(self.configs),
            "deployments_total": len(self.deployments),
            "deployments_active": active,
            "targets_supported": self.SUPPORTED_TARGETS,
        }

    def to_dict(self) -> Dict:
        return {
            "configs": [c.to_dict() for c in self.configs.values()],
            "deployments": [d.to_dict() for d in self.deployments.values()],
            "stats": self.get_stats(),
        }


__all__ = ["AgentsDeploy", "DeploymentConfig", "DeploymentRecord"]
