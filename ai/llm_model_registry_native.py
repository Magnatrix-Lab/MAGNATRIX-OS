"""Model Registry — Model versioning, comparison, deployment tracking, and model zoo.

Modul ini menyediakan:
- ModelRegistry untuk register/unregister models dengan metadata
- ModelComparator untuk compare models across metrics
- DeploymentTracker untuk track deployment history
- ModelZoo untuk curated model collection
- ModelRegistryManager untuk centralized model management
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ModelStatus(Enum):
    RESEARCH = auto()
    STAGING = auto()
    PRODUCTION = auto()
    ARCHIVED = auto()
    DEPRECATED = auto()


class ModelCapability(Enum):
    TEXT = auto()
    CODE = auto()
    VISION = auto()
    AUDIO = auto()
    MULTIMODAL = auto()
    REASONING = auto()
    EMBEDDING = auto()


@dataclass
class ModelInfo:
    """Model metadata."""
    model_id: str
    name: str
    version: str
    family: str
    status: ModelStatus = ModelStatus.RESEARCH
    capabilities: Set[ModelCapability] = field(default_factory=set)
    parameters: int = 0  # in millions
    context_length: int = 4096
    quantization: str = "fp16"
    size_mb: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    deployed_at: Optional[float] = None
    checkpoint_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "version": self.version,
            "family": self.family,
            "status": self.status.name,
            "capabilities": [c.name for c in self.capabilities],
            "parameters_m": self.parameters,
            "context_length": self.context_length,
            "size_mb": self.size_mb,
            "metrics": self.metrics,
        }


@dataclass
class DeploymentRecord:
    """Model deployment record."""
    deployment_id: str
    model_id: str
    environment: str
    deployed_at: float
    rollback_at: Optional[float] = None
    traffic_percent: float = 0.0
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelComparator:
    """Compare models across metrics."""

    def __init__(self):
        self._metrics: List[str] = []

    def compare(self, models: List[ModelInfo], metrics: List[str]) -> Dict[str, Any]:
        results = {}
        for metric in metrics:
            scores = {}
            for m in models:
                scores[m.model_id] = m.metrics.get(metric, 0.0)
            best = max(scores, key=scores.get)
            results[metric] = {
                "best": best,
                "best_score": scores[best],
                "all_scores": scores,
            }
        # Overall ranking
        overall = {}
        for m in models:
            total = sum(m.metrics.get(k, 0.0) for k in metrics)
            overall[m.model_id] = total / max(len(metrics), 1)
        best_overall = max(overall, key=overall.get)
        results["overall"] = {
            "best": best_overall,
            "best_score": overall[best_overall],
            "rankings": sorted(overall.items(), key=lambda x: x[1], reverse=True),
        }
        return results

    def benchmark(self, model: ModelInfo, benchmark_fn: Callable[[ModelInfo], Dict[str, float]]) -> Dict[str, float]:
        return benchmark_fn(model)


class DeploymentTracker:
    """Track model deployment history."""

    def __init__(self):
        self._deployments: List[DeploymentRecord] = []
        self._current: Dict[str, str] = {}  # environment -> model_id

    def deploy(self, model_id: str, environment: str, traffic_percent: float = 100.0) -> DeploymentRecord:
        # Demote current
        if environment in self._current:
            for dep in self._deployments:
                if dep.model_id == self._current[environment] and dep.environment == environment and dep.status == "active":
                    dep.status = "archived"
        dep = DeploymentRecord(
            deployment_id=str(uuid.uuid4())[:12],
            model_id=model_id,
            environment=environment,
            deployed_at=time.time(),
            traffic_percent=traffic_percent,
        )
        self._deployments.append(dep)
        self._current[environment] = model_id
        return dep

    def rollback(self, environment: str) -> Optional[str]:
        active = [d for d in self._deployments if d.environment == environment and d.status == "active"]
        if not active:
            return None
        current = active[-1]
        current.status = "rolled_back"
        current.rollback_at = time.time()
        # Find previous
        previous = [d for d in self._deployments if d.environment == environment and d.status == "archived"]
        if previous:
            prev = previous[-1]
            prev.status = "active"
            self._current[environment] = prev.model_id
            return prev.model_id
        return None

    def get_history(self, environment: Optional[str] = None) -> List[DeploymentRecord]:
        if environment:
            return [d for d in self._deployments if d.environment == environment]
        return self._deployments

    def get_current(self, environment: str) -> Optional[str]:
        return self._current.get(environment)


class ModelZoo:
    """Curated collection of models."""

    def __init__(self):
        self._models: Dict[str, ModelInfo] = {}
        self._collections: Dict[str, List[str]] = {}  # collection_name -> model_ids

    def add(self, model: ModelInfo) -> None:
        self._models[model.model_id] = model

    def add_to_collection(self, model_id: str, collection: str) -> None:
        self._collections.setdefault(collection, []).append(model_id)

    def get_collection(self, collection: str) -> List[ModelInfo]:
        ids = self._collections.get(collection, [])
        return [self._models[i] for i in ids if i in self._models]

    def find_by_capability(self, capability: ModelCapability) -> List[ModelInfo]:
        return [m for m in self._models.values() if capability in m.capabilities]

    def find_by_family(self, family: str) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.family == family]

    def get_recommendation(self, task: str, min_params: int = 0) -> List[ModelInfo]:
        # Simple task-capability mapping
        task_caps = {
            "coding": ModelCapability.CODE,
            "chat": ModelCapability.TEXT,
            "vision": ModelCapability.VISION,
            "reasoning": ModelCapability.REASONING,
            "embedding": ModelCapability.EMBEDDING,
        }
        cap = task_caps.get(task.lower(), ModelCapability.TEXT)
        candidates = self.find_by_capability(cap)
        candidates = [m for m in candidates if m.parameters >= min_params]
        return sorted(candidates, key=lambda m: m.metrics.get("accuracy", 0), reverse=True)


class ModelRegistryManager:
    """Centralized model management."""

    def __init__(self):
        self.registry: Dict[str, ModelInfo] = {}
        self.comparator = ModelComparator()
        self.tracker = DeploymentTracker()
        self.zoo = ModelZoo()

    def register(self, model: ModelInfo) -> None:
        self.registry[model.model_id] = model
        self.zoo.add(model)

    def get(self, model_id: str) -> Optional[ModelInfo]:
        return self.registry.get(model_id)

    def promote(self, model_id: str, status: ModelStatus) -> bool:
        model = self.registry.get(model_id)
        if model:
            model.status = status
            if status == ModelStatus.PRODUCTION:
                model.deployed_at = time.time()
            return True
        return False

    def deploy(self, model_id: str, environment: str, traffic_percent: float = 100.0) -> Optional[DeploymentRecord]:
        if model_id not in self.registry:
            return None
        self.promote(model_id, ModelStatus.PRODUCTION)
        return self.tracker.deploy(model_id, environment, traffic_percent)

    def compare_models(self, model_ids: List[str], metrics: List[str]) -> Dict[str, Any]:
        models = [self.registry.get(m) for m in model_ids if m in self.registry]
        models = [m for m in models if m]
        return self.comparator.compare(models, metrics)

    def list_by_status(self, status: ModelStatus) -> List[ModelInfo]:
        return [m for m in self.registry.values() if m.status == status]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_models": len(self.registry),
            "production": len(self.list_by_status(ModelStatus.PRODUCTION)),
            "staging": len(self.list_by_status(ModelStatus.STAGING)),
            "research": len(self.list_by_status(ModelStatus.RESEARCH)),
            "deployments": len(self.tracker._deployments),
            "environments": len(self.tracker._current),
        }

    def export_registry(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "models": [m.to_dict() for m in self.registry.values()],
                "stats": self.get_stats(),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MODEL REGISTRY DEMO")
    print("=" * 70)

    manager = ModelRegistryManager()

    # 1. Register models
    print("\n[1] Register Models")
    models = [
        ModelInfo("m1", "Llama-3-8B", "3.0", "llama", parameters=8000, context_length=8192, size_mb=16000,
                  capabilities={ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.REASONING},
                  metrics={"accuracy": 0.72, "mmlu": 0.68, "humaneval": 0.45}),
        ModelInfo("m2", "Llama-3-70B", "3.0", "llama", parameters=70000, context_length=8192, size_mb=140000,
                  capabilities={ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.REASONING},
                  metrics={"accuracy": 0.85, "mmlu": 0.82, "humaneval": 0.62}),
        ModelInfo("m3", "GPT-4", "turbo", "gpt", parameters=1800000, context_length=128000, size_mb=3600000,
                  capabilities={ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.REASONING, ModelCapability.VISION},
                  metrics={"accuracy": 0.89, "mmlu": 0.87, "humaneval": 0.85}),
        ModelInfo("m4", "Claude-3.5", "sonnet", "claude", parameters=175000, context_length=200000, size_mb=350000,
                  capabilities={ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.REASONING, ModelCapability.VISION},
                  metrics={"accuracy": 0.88, "mmlu": 0.86, "humaneval": 0.82}),
        ModelInfo("m5", "CodeLlama-7B", "1.0", "codellama", parameters=7000, context_length=16384, size_mb=14000,
                  capabilities={ModelCapability.CODE, ModelCapability.TEXT},
                  metrics={"accuracy": 0.65, "mmlu": 0.55, "humaneval": 0.58}),
    ]
    for m in models:
        manager.register(m)
    print(f"  Registered: {len(manager.registry)} models")

    # 2. Collections
    print("\n[2] Model Collections")
    manager.zoo.add_to_collection("m1", "open_source")
    manager.zoo.add_to_collection("m2", "open_source")
    manager.zoo.add_to_collection("m5", "open_source")
    manager.zoo.add_to_collection("m3", "commercial")
    manager.zoo.add_to_collection("m4", "commercial")
    oss = manager.zoo.get_collection("open_source")
    print(f"  Open source: {[m.name for m in oss]}")

    # 3. Compare
    print("\n[3] Model Comparison")
    comparison = manager.compare_models(["m1", "m2", "m3", "m4"], ["accuracy", "mmlu", "humaneval"])
    for metric, result in comparison.items():
        if metric != "overall":
            best = manager.get(result["best"])
            print(f"  {metric}: {best.name} = {result['best_score']:.2f}")
    print(f"  Overall best: {manager.get(comparison['overall']['best']).name}")

    # 4. Deploy
    print("\n[4] Deployment")
    dep1 = manager.deploy("m2", "production", 100.0)
    print(f"  Deployed Llama-3-70B to production: {dep1.deployment_id}")
    dep2 = manager.deploy("m3", "production", 20.0)
    print(f"  Deployed GPT-4 to production (20% traffic): {dep2.deployment_id}")
    print(f"  Current production: {manager.tracker.get_current('production')}")

    # 5. Rollback
    print("\n[5] Rollback")
    rolled = manager.tracker.rollback("production")
    print(f"  Rolled back to: {rolled}")
    print(f"  Current production: {manager.tracker.get_current('production')}")

    # 6. Recommendations
    print("\n[6] Recommendations")
    for task in ["coding", "chat", "reasoning"]:
        recs = manager.zoo.get_recommendation(task, min_params=1000)
        print(f"  {task}: {recs[0].name if recs else 'None'}")

    # 7. Find by capability
    print("\n[7] Vision Models")
    vision = manager.zoo.find_by_capability(ModelCapability.VISION)
    print(f"  {[m.name for m in vision]}")

    # 8. Stats
    print(f"\n[8] Stats")
    print(f"  {manager.get_stats()}")

    # 9. Export
    print("\n[9] Export")
    manager.export_registry("/tmp/model_registry.json")
    print("  Exported to /tmp/model_registry.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
