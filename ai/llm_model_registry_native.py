"""
llm_model_registry_native.py
MAGNATRIX-OS Model Registry Engine
Native Python, stdlib only.
Provides model versioning, artifact tracking, stage transitions, and deployment metadata.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class ModelStage(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class ModelStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRAINING = "training"
    FAILED = "failed"


@dataclass
class ModelArtifact:
    path: str
    checksum: str
    size_bytes: int
    format: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "checksum": self.checksum, "size_bytes": self.size_bytes,
                "format": self.format, "metadata": self.metadata}


@dataclass
class ModelVersion:
    version: str
    model_id: str
    stage: ModelStage
    status: ModelStatus
    artifacts: List[ModelArtifact]
    metrics: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    trained_by: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version, "model_id": self.model_id,
            "stage": self.stage.value, "status": self.status.value,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "metrics": self.metrics, "params": self.params,
            "tags": self.tags, "created_at": self.created_at,
            "trained_by": self.trained_by, "description": self.description,
        }


@dataclass
class Model:
    id: str
    name: str
    description: str
    framework: str
    task_type: str
    owner: str
    versions: Dict[str, ModelVersion] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "framework": self.framework, "task_type": self.task_type,
            "owner": self.owner, "tags": self.tags, "metadata": self.metadata,
            "created_at": self.created_at,
            "versions": {k: v.to_dict() for k, v in self.versions.items()},
        }

    def latest_version(self) -> Optional[ModelVersion]:
        if not self.versions:
            return None
        return max(self.versions.values(), key=lambda v: v.created_at)

    def production_version(self) -> Optional[ModelVersion]:
        prod = [v for v in self.versions.values() if v.stage == ModelStage.PRODUCTION]
        if not prod:
            return None
        return max(prod, key=lambda v: v.created_at)


class ModelRegistryEngine:
    """
    Model registry with versioning, stage management, and artifact tracking.
    """

    def __init__(self) -> None:
        self._models: Dict[str, Model] = {}
        self._name_index: Dict[str, str] = {}  # name -> id
        self._tag_index: Dict[str, List[str]] = {}  # tag -> [model_ids]
        self._stage_index: Dict[str, List[str]] = {}  # stage -> [(model_id, version)]

    def register_model(self, model: Model) -> None:
        self._models[model.id] = model
        self._name_index[model.name] = model.id
        for tag in model.tags:
            self._tag_index.setdefault(tag, []).append(model.id)

    def create_version(self, model_id: str, version: ModelVersion) -> bool:
        if model_id not in self._models:
            return False
        model = self._models[model_id]
        model.versions[version.version] = version
        self._stage_index.setdefault(version.stage.value, []).append((model_id, version.version))
        return True

    def get_model(self, model_id: str) -> Optional[Model]:
        return self._models.get(model_id)

    def get_version(self, model_id: str, version: str) -> Optional[ModelVersion]:
        model = self._models.get(model_id)
        if not model:
            return None
        return model.versions.get(version)

    def transition_stage(self, model_id: str, version: str, new_stage: ModelStage) -> bool:
        v = self.get_version(model_id, version)
        if not v:
            return False
        old_stage = v.stage
        v.stage = new_stage
        # Update index
        if old_stage.value in self._stage_index:
            self._stage_index[old_stage.value] = [x for x in self._stage_index[old_stage.value]
                                                   if not (x[0] == model_id and x[1] == version)]
        self._stage_index.setdefault(new_stage.value, []).append((model_id, version))
        return True

    def list_models(self, tag: Optional[str] = None, framework: Optional[str] = None) -> List[Model]:
        models = list(self._models.values())
        if tag:
            ids = set(self._tag_index.get(tag, []))
            models = [m for m in models if m.id in ids]
        if framework:
            models = [m for m in models if m.framework == framework]
        return models

    def list_versions(self, model_id: str, stage: Optional[ModelStage] = None) -> List[ModelVersion]:
        model = self._models.get(model_id)
        if not model:
            return []
        versions = list(model.versions.values())
        if stage:
            versions = [v for v in versions if v.stage == stage]
        return sorted(versions, key=lambda v: v.created_at, reverse=True)

    def compare_versions(self, model_id: str, v1: str, v2: str) -> Dict[str, Any]:
        version1 = self.get_version(model_id, v1)
        version2 = self.get_version(model_id, v2)
        if not version1 or not version2:
            return {"error": "Version not found"}
        return {
            "metrics_diff": {k: {"v1": version1.metrics.get(k), "v2": version2.metrics.get(k)}
                             for k in set(version1.metrics) | set(version2.metrics)},
            "params_diff": {k: {"v1": version1.params.get(k), "v2": version2.params.get(k)}
                            for k in set(version1.params) | set(version2.params)},
            "stage": {"v1": version1.stage.value, "v2": version2.stage.value},
        }

    def deprecate_version(self, model_id: str, version: str) -> bool:
        v = self.get_version(model_id, version)
        if not v:
            return False
        v.status = ModelStatus.INACTIVE
        v.stage = ModelStage.DEPRECATED
        return True

    def search(self, query: str) -> List[Model]:
        query_lower = query.lower()
        results = []
        for model in self._models.values():
            score = 0
            if query_lower in model.name.lower():
                score += 10
            if query_lower in model.description.lower():
                score += 5
            if query_lower in model.framework.lower():
                score += 3
            if score > 0:
                results.append((score, model))
        results.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in results]

    def export_registry(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in self._models.values()], f, indent=2, default=str)

    def stats(self) -> Dict[str, Any]:
        total_versions = sum(len(m.versions) for m in self._models.values())
        prod_versions = len(self._stage_index.get(ModelStage.PRODUCTION.value, []))
        return {
            "models": len(self._models),
            "total_versions": total_versions,
            "production_versions": prod_versions,
            "frameworks": list(set(m.framework for m in self._models.values())),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Model Registry Engine")
    print("=" * 60)

    engine = ModelRegistryEngine()

    # Register models
    model1 = Model(
        id="m1", name="churn_predictor", description="Predicts customer churn probability",
        framework="xgboost", task_type="classification", owner="ml_team",
        tags=["core", "classification"]
    )
    engine.register_model(model1)

    # Create versions
    v1 = ModelVersion(
        version="1.0.0", model_id="m1", stage=ModelStage.DEVELOPMENT,
        status=ModelStatus.ACTIVE, artifacts=[ModelArtifact("s3://models/v1", "abc123", 1024000, "pkl")],
        metrics={"accuracy": 0.85, "f1": 0.82}, params={"max_depth": 6, "learning_rate": 0.1},
        tags=["baseline"], trained_by="user_a", description="Initial model"
    )
    v2 = ModelVersion(
        version="1.1.0", model_id="m1", stage=ModelStage.STAGING,
        status=ModelStatus.ACTIVE, artifacts=[ModelArtifact("s3://models/v2", "def456", 1050000, "pkl")],
        metrics={"accuracy": 0.89, "f1": 0.87}, params={"max_depth": 8, "learning_rate": 0.05},
        tags=["improved"], trained_by="user_b", description="Tuned hyperparameters"
    )
    v3 = ModelVersion(
        version="2.0.0", model_id="m1", stage=ModelStage.PRODUCTION,
        status=ModelStatus.ACTIVE, artifacts=[ModelArtifact("s3://models/v3", "ghi789", 1100000, "pkl")],
        metrics={"accuracy": 0.92, "f1": 0.90}, params={"max_depth": 10, "learning_rate": 0.03},
        tags=["prod"], trained_by="user_c", description="Final production model"
    )

    for v in [v1, v2, v3]:
        engine.create_version("m1", v)

    print("\n--- Stats ---")
    print(engine.stats())

    print("\n--- Latest Version ---")
    latest = engine.get_model("m1").latest_version()
    print(f"  {latest.version} (stage={latest.stage.value})")

    print("\n--- Production Version ---")
    prod = engine.get_model("m1").production_version()
    print(f"  {prod.version} metrics={prod.metrics}")

    print("\n--- Compare v1.0.0 vs v2.0.0 ---")
    diff = engine.compare_versions("m1", "1.0.0", "2.0.0")
    print(f"  metrics_diff: {diff['metrics_diff']}")
    print(f"  params_diff: {diff['params_diff']}")

    print("\n--- Transition v2.0.0 to ARCHIVED ---")
    engine.transition_stage("m1", "2.0.0", ModelStage.ARCHIVED)
    print(f"  v2.0.0 stage: {engine.get_version('m1', '2.0.0').stage.value}")

    print("\n--- Search: 'churn' ---")
    results = engine.search("churn")
    for m in results:
        print(f"  {m.name} ({m.framework})")

    print("\nModel Registry test complete.")


if __name__ == "__main__":
    run()
