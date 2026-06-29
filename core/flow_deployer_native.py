"""
flow_deployer_native.py
MAGNATRIX-OS — Flow Deployer

Inspired by langflow-ai/langflow API deployment:
Deploy flows as APIs with endpoint generation and request handling. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class DeployedEndpoint:
    endpoint_id: str
    flow_id: str
    path: str
    method: str
    is_active: bool = True
    created_at: str = ""
    request_count: int = 0
    avg_latency_ms: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class FlowDeployer:
    """Deploy flows as APIs with endpoint generation."""

    def __init__(self, deploy_dir: str = "./deployed_flows"):
        self.deploy_dir = Path(deploy_dir)
        self.deploy_dir.mkdir(exist_ok=True)
        self.endpoints: Dict[str, DeployedEndpoint] = {}
        self._load()

    def _load(self) -> None:
        file = self.deploy_dir / "endpoints.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for eid, ed in data.items():
                        self.endpoints[eid] = DeployedEndpoint(**ed)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.deploy_dir / "endpoints.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.endpoints.items()}, f, indent=2)

    def deploy(self, flow_id: str, endpoint_path: str, method: str = "POST") -> DeployedEndpoint:
        endpoint_id = f"{flow_id}_{method.lower()}"
        endpoint = DeployedEndpoint(
            endpoint_id=endpoint_id, flow_id=flow_id, path=endpoint_path, method=method,
        )
        self.endpoints[endpoint_id] = endpoint
        self._save()
        return endpoint

    def undeploy(self, endpoint_id: str) -> bool:
        if endpoint_id in self.endpoints:
            self.endpoints[endpoint_id].is_active = False
            self._save()
            return True
        return False

    def record_request(self, endpoint_id: str, latency_ms: float) -> bool:
        endpoint = self.endpoints.get(endpoint_id)
        if not endpoint:
            return False
        endpoint.request_count += 1
        # Update rolling average
        n = endpoint.request_count
        endpoint.avg_latency_ms = ((endpoint.avg_latency_ms * (n - 1)) + latency_ms) / n
        self._save()
        return True

    def get_endpoint(self, endpoint_id: str) -> Optional[DeployedEndpoint]:
        return self.endpoints.get(endpoint_id)

    def get_active_endpoints(self) -> List[DeployedEndpoint]:
        return [e for e in self.endpoints.values() if e.is_active]

    def generate_openapi_spec(self, flow_id: str) -> Dict[str, Any]:
        """Generate OpenAPI-like spec for a deployed flow."""
        return {
            "openapi": "3.0.0", "info": {"title": f"Flow {flow_id}", "version": "1.0.0"},
            "paths": {
                f"/api/v1/flows/{flow_id}": {
                    "post": {
                        "summary": f"Execute flow {flow_id}",
                        "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                        "responses": {"200": {"description": "Flow execution result"}},
                    }
                }
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        active = len(self.get_active_endpoints())
        total_req = sum(e.request_count for e in self.endpoints.values())
        return {"endpoints": len(self.endpoints), "active": active, "total_requests": total_req}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["FlowDeployer", "DeployedEndpoint"]