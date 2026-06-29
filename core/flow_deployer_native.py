"""
flow_deployer_native.py
MAGNATRIX-OS — Flow Deployer

Inspired by Langflow (langflow-ai): Deploy flows as APIs, webhooks, or scheduled jobs.
Deployment manager with environment configs and versioning. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Deployment:
    deployment_id: str
    flow_id: str
    name: str
    deployment_type: str  # api, webhook, scheduled
    config: Dict[str, Any] = field(default_factory=dict)
    status: str = "inactive"
    endpoint: str = ""
    created_at: str = ""
    last_deployed: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class FlowDeployer:
    """Deploy flows as APIs, webhooks, or scheduled jobs with versioning."""

    def __init__(self, deploy_dir: str = "./deployments"):
        self.deploy_dir = Path(deploy_dir)
        self.deploy_dir.mkdir(exist_ok=True)
        self.deployments: Dict[str, Deployment] = {}
        self._load()

    def _load(self) -> None:
        file = self.deploy_dir / "deployments.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for did, dd in data.items():
                        self.deployments[did] = Deployment(**dd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.deploy_dir / "deployments.json", "w", encoding="utf-8") as f:
            json.dump({did: asdict(d) for did, d in self.deployments.items()}, f, indent=2)

    def deploy(self, deployment_id: str, flow_id: str, name: str, deployment_type: str,
               config: Optional[Dict[str, Any]] = None) -> Deployment:
        dep = Deployment(
            deployment_id=deployment_id, flow_id=flow_id, name=name,
            deployment_type=deployment_type, config=config or {},
            status="active", endpoint=f"/api/v1/flows/{flow_id}/run",
            last_deployed=datetime.now().isoformat(),
        )
        self.deployments[deployment_id] = dep
        self._save()
        return dep

    def undeploy(self, deployment_id: str) -> bool:
        dep = self.deployments.get(deployment_id)
        if not dep:
            return False
        dep.status = "inactive"
        dep.endpoint = ""
        self._save()
        return True

    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        return self.deployments.get(deployment_id)

    def list_deployments(self, flow_id: Optional[str] = None) -> List[Deployment]:
        if flow_id:
            return [d for d in self.deployments.values() if d.flow_id == flow_id]
        return list(self.deployments.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.deployments)
        active = sum(1 for d in self.deployments.values() if d.status == "active")
        return {"total": total, "active": active, "inactive": total - active}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["FlowDeployer", "Deployment"]