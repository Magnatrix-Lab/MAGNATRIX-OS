"""Model Registry — version tracking, metadata, artifact management, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto
import time
import hashlib

class ModelStatus(Enum):
    DEVELOPMENT = auto()
    STAGING = auto()
    PRODUCTION = auto()
    ARCHIVED = auto()
    DEPRECATED = auto()

@dataclass
class ModelVersion:
    version_id: str
    model_name: str
    version: str
    status: ModelStatus
    metrics: Dict[str, float]
    created_at: float
    checksum: str
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

class ModelRegistry:
    def __init__(self):
        self.models: Dict[str, List[ModelVersion]] = {}
        self.aliases: Dict[str, str] = {}

    def register(self, model_name: str, version: str, metrics: Dict[str, float], artifacts: Dict[str, Any] = None, tags: List[str] = None) -> ModelVersion:
        artifacts = artifacts or {}
        checksum = hashlib.sha256(str(sorted(artifacts.items())).encode()).hexdigest()[:8]
        mv = ModelVersion(
            f"{model_name}:{version}", model_name, version, ModelStatus.DEVELOPMENT,
            metrics, time.time(), checksum, tags or []
        )
        if model_name not in self.models:
            self.models[model_name] = []
        self.models[model_name].append(mv)
        return mv

    def promote(self, model_name: str, version: str, status: ModelStatus):
        for mv in self.models.get(model_name, []):
            if mv.version == version:
                mv.status = status
                return True
        return False

    def set_alias(self, alias: str, model_name: str, version: str):
        self.aliases[alias] = f"{model_name}:{version}"

    def get_by_alias(self, alias: str) -> Optional[ModelVersion]:
        key = self.aliases.get(alias)
        if not key:
            return None
        name, version = key.split(":")
        for mv in self.models.get(name, []):
            if mv.version == version:
                return mv
        return None

    def get_production(self, model_name: str) -> Optional[ModelVersion]:
        for mv in self.models.get(model_name, []):
            if mv.status == ModelStatus.PRODUCTION:
                return mv
        return None

    def list_versions(self, model_name: str) -> List[ModelVersion]:
        return self.models.get(model_name, [])

    def compare_versions(self, model_name: str, v1: str, v2: str) -> Dict:
        mv1 = next((mv for mv in self.models.get(model_name, []) if mv.version == v1), None)
        mv2 = next((mv for mv in self.models.get(model_name, []) if mv.version == v2), None)
        if not mv1 or not mv2:
            return {}
        return {k: (mv1.metrics.get(k), mv2.metrics.get(k)) for k in set(mv1.metrics) | set(mv2.metrics)}

    def stats(self) -> Dict:
        total = sum(len(v) for v in self.models.values())
        return {"models": len(self.models), "versions": total, "aliases": len(self.aliases)}

def run():
    registry = ModelRegistry()
    registry.register("classifier", "v1", {"accuracy": 0.85, "f1": 0.82}, tags=["baseline"])
    registry.register("classifier", "v2", {"accuracy": 0.91, "f1": 0.90}, tags=["improved"])
    registry.promote("classifier", "v2", ModelStatus.PRODUCTION)
    registry.set_alias("latest", "classifier", "v2")
    print(registry.get_by_alias("latest"))
    print(registry.compare_versions("classifier", "v1", "v2"))
    print(registry.stats())

if __name__ == "__main__":
    run()
