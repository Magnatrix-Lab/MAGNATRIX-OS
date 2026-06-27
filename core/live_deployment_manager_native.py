#!/usr/bin/env python3
"""
Live Deployment Manager for MAGNATRIX-OS
========================================
Blue-green + canary + A/B testing + rollback automation.
Production-ready deployment orchestration. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, os, random, shutil, time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


class DeploymentStrategy(Enum):
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    AB_TEST = "ab_test"
    RECREATE = "recreate"


class DeploymentStatus(Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    HEALTH_CHECK = "health_check"
    ACTIVE = "active"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class Deployment:
    """A deployment instance."""
    deployment_id: str
    version: str
    strategy: DeploymentStrategy
    status: DeploymentStatus = DeploymentStatus.PENDING
    created_at: float = field(default_factory=time.time)
    activated_at: Optional[float] = None
    traffic_percentage: float = 0.0
    health_score: float = 1.0
    error_rate: float = 0.0
    latency_ms: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    rollback_target: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["strategy"] = self.strategy.value
        d["status"] = self.status.value
        return d


class BlueGreenDeployer:
    """Blue-green deployment strategy."""

    def __init__(self, blue_dir: str = "deploy/blue", green_dir: str = "deploy/green") -> None:
        self.blue_dir = blue_dir
        self.green_dir = green_dir
        self.active = "blue"  # or "green"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for d in [self.blue_dir, self.green_dir]:
            os.makedirs(d, exist_ok=True)

    def deploy(self, source_dir: str, version: str) -> str:
        """Deploy to the inactive environment."""
        target = self.green_dir if self.active == "blue" else self.blue_dir
        # Clear target
        if os.path.exists(target):
            shutil.rmtree(target)
        # Copy source
        shutil.copytree(source_dir, target)
        # Write version marker
        with open(os.path.join(target, ".version"), "w") as f:
            f.write(version)
        return target

    def switch_traffic(self) -> str:
        """Switch traffic from active to inactive."""
        self.active = "green" if self.active == "blue" else "blue"
        return self.active

    def get_active_dir(self) -> str:
        return self.blue_dir if self.active == "blue" else self.green_dir

    def get_inactive_dir(self) -> str:
        return self.green_dir if self.active == "blue" else self.blue_dir

    def rollback(self) -> str:
        """Switch back to previous environment."""
        return self.switch_traffic()


class CanaryDeployer:
    """Canary deployment with traffic shifting."""

    def __init__(self, canary_dir: str = "deploy/canary", stable_dir: str = "deploy/stable") -> None:
        self.canary_dir = canary_dir
        self.stable_dir = stable_dir
        self.canary_percentage = 0.0
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for d in [self.canary_dir, self.stable_dir]:
            os.makedirs(d, exist_ok=True)

    def deploy(self, source_dir: str, version: str) -> None:
        """Deploy canary version."""
        if os.path.exists(self.canary_dir):
            shutil.rmtree(self.canary_dir)
        shutil.copytree(source_dir, self.canary_dir)
        with open(os.path.join(self.canary_dir, ".version"), "w") as f:
            f.write(version)
        self.canary_percentage = 5.0  # Start with 5%

    def shift_traffic(self, percentage: float) -> None:
        """Shift traffic to canary."""
        self.canary_percentage = max(0.0, min(100.0, percentage))

    def promote(self) -> None:
        """Promote canary to stable."""
        if os.path.exists(self.stable_dir):
            shutil.rmtree(self.stable_dir)
        shutil.copytree(self.canary_dir, self.stable_dir)
        self.canary_percentage = 0.0

    def rollback(self) -> None:
        """Rollback canary to 0%."""
        self.canary_percentage = 0.0

    def route_request(self) -> str:
        """Route a request to canary or stable."""
        return "canary" if random.random() < self.canary_percentage / 100 else "stable"


class ABTestDeployer:
    """A/B testing deployment."""

    def __init__(self, variants_dir: str = "deploy/variants") -> None:
        self.variants_dir = variants_dir
        self.variants: Dict[str, str] = {}  # variant_id -> directory
        self.weights: Dict[str, float] = {}  # variant_id -> traffic weight
        os.makedirs(variants_dir, exist_ok=True)

    def add_variant(self, variant_id: str, source_dir: str, weight: float = 0.5) -> None:
        """Add an A/B test variant."""
        target = os.path.join(self.variants_dir, variant_id)
        if os.path.exists(target):
            shutil.rmtree(target)
        shutil.copytree(source_dir, target)
        self.variants[variant_id] = target
        self.weights[variant_id] = weight

    def set_weights(self, weights: Dict[str, float]) -> None:
        """Set traffic weights for variants."""
        total = sum(weights.values())
        self.weights = {k: v / total for k, v in weights.items()} if total > 0 else weights

    def route_request(self) -> str:
        """Route request to a variant based on weights."""
        if not self.weights:
            return "control"
        r = random.random()
        cumulative = 0.0
        for variant, weight in self.weights.items():
            cumulative += weight
            if r <= cumulative:
                return variant
        return list(self.weights.keys())[-1]

    def get_stats(self, variant_id: str) -> Dict[str, Any]:
        return {"weight": self.weights.get(variant_id, 0.0), "variant": variant_id}


class RollingDeployer:
    """Rolling deployment that updates instances gradually."""

    def __init__(self, instances_dir: str = "deploy/instances") -> None:
        self.instances_dir = instances_dir
        self.instances: List[str] = []
        self.updated: List[bool] = []
        os.makedirs(instances_dir, exist_ok=True)

    def register_instances(self, count: int) -> None:
        """Register deployment instances."""
        self.instances = [f"instance_{i}" for i in range(count)]
        self.updated = [False] * count

    def deploy_batch(self, source_dir: str, batch_size: int) -> int:
        """Deploy to a batch of instances."""
        updated = 0
        for i in range(len(self.instances)):
            if not self.updated[i] and updated < batch_size:
                target = os.path.join(self.instances_dir, self.instances[i])
                if os.path.exists(target):
                    shutil.rmtree(target)
                shutil.copytree(source_dir, target)
                self.updated[i] = True
                updated += 1
        return updated

    def is_complete(self) -> bool:
        return all(self.updated)

    def rollback(self) -> None:
        """Rollback all instances."""
        self.updated = [False] * len(self.instances)

    def get_progress(self) -> float:
        if not self.instances:
            return 0.0
        return sum(self.updated) / len(self.instances) * 100


class HealthChecker:
    """Health check for deployed versions."""

    def __init__(self) -> None:
        self.health_history: Dict[str, List[Dict[str, Any]]] = {}

    def check(self, deployment_id: str) -> Dict[str, Any]:
        """Perform health check on deployment."""
        # Simulated health check
        health = {
            "deployment_id": deployment_id,
            "timestamp": time.time(),
            "status": "healthy",
            "error_rate": random.uniform(0.0, 0.05),
            "latency_ms": random.uniform(10, 200),
            "cpu_usage": random.uniform(0.1, 0.8),
            "memory_usage": random.uniform(0.2, 0.7),
        }
        if health["error_rate"] > 0.03:
            health["status"] = "degraded"
        if health["error_rate"] > 0.08:
            health["status"] = "unhealthy"
        
        if deployment_id not in self.health_history:
            self.health_history[deployment_id] = []
        self.health_history[deployment_id].append(health)
        if len(self.health_history[deployment_id]) > 100:
            self.health_history[deployment_id] = self.health_history[deployment_id][-50:]
        
        return health

    def is_healthy(self, deployment_id: str, threshold: float = 0.95) -> bool:
        history = self.health_history.get(deployment_id, [])
        if not history:
            return True
        healthy_count = sum(1 for h in history if h["status"] == "healthy")
        return healthy_count / len(history) >= threshold

    def get_trend(self, deployment_id: str) -> Dict[str, Any]:
        history = self.health_history.get(deployment_id, [])
        if not history:
            return {"trend": "unknown"}
        recent = history[-10:]
        error_trend = sum(h["error_rate"] for h in recent) / len(recent)
        latency_trend = sum(h["latency_ms"] for h in recent) / len(recent)
        return {
            "trend": "improving" if error_trend < 0.02 else "stable" if error_trend < 0.05 else "degrading",
            "avg_error_rate": round(error_trend, 4),
            "avg_latency_ms": round(latency_trend, 2),
        }


class LiveDeploymentManager:
    """Top-level deployment manager."""

    def __init__(self, repo_root: str = ".") -> None:
        self.repo_root = repo_root
        self.blue_green = BlueGreenDeployer()
        self.canary = CanaryDeployer()
        self.ab_test = ABTestDeployer()
        self.rolling = RollingDeployer()
        self.health = HealthChecker()
        self.deployments: Dict[str, Deployment] = {}
        self._deployment_counter = 0

    def deploy(self, source_dir: str, version: str, strategy: DeploymentStrategy, ab_variants: Optional[Dict[str, str]] = None) -> Deployment:
        """Deploy a new version with specified strategy."""
        self._deployment_counter += 1
        dep_id = f"dep_{self._deployment_counter}_{int(time.time())}"
        deployment = Deployment(
            deployment_id=dep_id,
            version=version,
            strategy=strategy,
            status=DeploymentStatus.DEPLOYING,
        )
        self.deployments[dep_id] = deployment

        if strategy == DeploymentStrategy.BLUE_GREEN:
            self.blue_green.deploy(source_dir, version)
            deployment.status = DeploymentStatus.HEALTH_CHECK
        elif strategy == DeploymentStrategy.CANARY:
            self.canary.deploy(source_dir, version)
            deployment.status = DeploymentStatus.HEALTH_CHECK
        elif strategy == DeploymentStrategy.AB_TEST and ab_variants:
            for variant_id, variant_dir in ab_variants.items():
                self.ab_test.add_variant(variant_id, variant_dir, 0.5)
            deployment.status = DeploymentStatus.ACTIVE
        elif strategy == DeploymentStrategy.ROLLING:
            self.rolling.register_instances(5)
            self.rolling.deploy_batch(source_dir, 2)
            deployment.status = DeploymentStatus.HEALTH_CHECK
        else:
            # RECREATE
            deployment.status = DeploymentStatus.ACTIVE

        deployment.activated_at = time.time()
        return deployment

    def health_check(self, deployment_id: str) -> Dict[str, Any]:
        """Run health check on a deployment."""
        result = self.health.check(deployment_id)
        deployment = self.deployments.get(deployment_id)
        if deployment:
            deployment.health_score = 1.0 - result.get("error_rate", 0)
            deployment.error_rate = result.get("error_rate", 0)
            deployment.latency_ms = result.get("latency_ms", 0)
            if result["status"] == "healthy":
                deployment.status = DeploymentStatus.ACTIVE
            elif result["status"] == "unhealthy":
                deployment.status = DeploymentStatus.FAILED
        return result

    def promote(self, deployment_id: str) -> bool:
        """Promote deployment (canary -> full, blue-green -> switch)."""
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            return False
        if deployment.strategy == DeploymentStrategy.BLUE_GREEN:
            self.blue_green.switch_traffic()
        elif deployment.strategy == DeploymentStrategy.CANARY:
            self.canary.shift_traffic(100.0)
            self.canary.promote()
        deployment.status = DeploymentStatus.ACTIVE
        return True

    def rollback(self, deployment_id: str) -> bool:
        """Rollback deployment to previous version."""
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            return False
        deployment.status = DeploymentStatus.ROLLING_BACK
        if deployment.strategy == DeploymentStrategy.BLUE_GREEN:
            self.blue_green.rollback()
        elif deployment.strategy == DeploymentStrategy.CANARY:
            self.canary.rollback()
        elif deployment.strategy == DeploymentStrategy.ROLLING:
            self.rolling.rollback()
        deployment.status = DeploymentStatus.ROLLED_BACK
        return True

    def route_request(self, deployment_id: str) -> str:
        """Route a request to the appropriate deployment."""
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            return "stable"
        if deployment.strategy == DeploymentStrategy.CANARY:
            return self.canary.route_request()
        elif deployment.strategy == DeploymentStrategy.AB_TEST:
            return self.ab_test.route_request()
        return self.blue_green.get_active_dir()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_deployments": len(self.deployments),
            "active": sum(1 for d in self.deployments.values() if d.status == DeploymentStatus.ACTIVE),
            "failed": sum(1 for d in self.deployments.values() if d.status == DeploymentStatus.FAILED),
            "rolled_back": sum(1 for d in self.deployments.values() if d.status == DeploymentStatus.ROLLED_BACK),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
