"""Canary Deployer — gradual rollout, traffic splitting, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum, auto
import random
import time
import hashlib

class CanaryStage(Enum):
    STAGING = auto()
    CANARY = auto()
    PRODUCTION = auto()
    ROLLBACK = auto()

@dataclass
class CanaryDeployment:
    deploy_id: str
    stage: CanaryStage
    canary_percentage: float
    metrics: Dict = field(default_factory=dict)
    errors: int = 0
    requests: int = 0

class CanaryDeployer:
    def __init__(self, error_threshold: float = 0.05, latency_threshold: float = 500.0):
        self.error_threshold = error_threshold
        self.latency_threshold = latency_threshold
        self.deployments: Dict[str, CanaryDeployment] = {}
        self.traffic_split: Dict[str, float] = {}

    def create_deployment(self, deploy_id: str, canary_pct: float = 5.0):
        self.deployments[deploy_id] = CanaryDeployment(deploy_id, CanaryStage.CANARY, canary_pct)
        self.traffic_split[deploy_id] = canary_pct

    def route_request(self, deploy_id: str, user_id: str) -> str:
        deploy = self.deployments.get(deploy_id)
        if not deploy:
            return "stable"
        h = hashlib.md5((deploy_id + user_id).encode()).hexdigest()
        bucket = int(h, 16) % 100
        if bucket < deploy.canary_percentage:
            deploy.requests += 1
            return "canary"
        return "stable"

    def record_metric(self, deploy_id: str, version: str, latency: float, error: bool):
        deploy = self.deployments.get(deploy_id)
        if not deploy:
            return
        if version == "canary":
            if error:
                deploy.errors += 1
            deploy.metrics["latency"] = deploy.metrics.get("latency", 0) + latency
            deploy.metrics["count"] = deploy.metrics.get("count", 0) + 1

    def promote(self, deploy_id: str):
        deploy = self.deployments.get(deploy_id)
        if deploy and self._healthy(deploy):
            deploy.canary_percentage = min(100, deploy.canary_percentage + 10)
            if deploy.canary_percentage >= 100:
                deploy.stage = CanaryStage.PRODUCTION

    def rollback(self, deploy_id: str):
        deploy = self.deployments.get(deploy_id)
        if deploy:
            deploy.stage = CanaryStage.ROLLBACK
            deploy.canary_percentage = 0

    def _healthy(self, deploy: CanaryDeployment) -> bool:
        if deploy.requests == 0:
            return True
        error_rate = deploy.errors / deploy.requests
        avg_latency = deploy.metrics.get("latency", 0) / deploy.metrics.get("count", 1)
        return error_rate < self.error_threshold and avg_latency < self.latency_threshold

    def stats(self) -> Dict:
        return {"deployments": len(self.deployments), "stages": {d.stage.name for d in self.deployments.values()}}

def run():
    deployer = CanaryDeployer()
    deployer.create_deployment("v2", 10)
    for i in range(20):
        route = deployer.route_request("v2", f"user{i}")
        deployer.record_metric("v2", route, random.randint(100, 600), random.random() < 0.02)
    deployer.promote("v2")
    print(deployer.stats())

if __name__ == "__main__":
    run()
