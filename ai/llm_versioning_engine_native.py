#!/usr/bin/env python3
"""
MAGNATRIX-OS — Model Versioning Engine
ai/llm_versioning_engine_native.py

Features:
- Model version tracking (semantic versioning, build IDs)
- Version comparison (diff between model versions)
- Rollback mechanism (restore previous version)
- Changelog generation (auto-generate from version history)
- Version metadata management (accuracy, latency, size, tags)
- Version promotion pipeline (dev → staging → prod)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("versioning")


class VersionStage(enum.Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"
    ARCHIVED = "archived"


@dataclass
class VersionMetrics:
    accuracy: float = 0.0
    latency_ms: float = 0.0
    size_mb: float = 0.0
    perplexity: float = 0.0


@dataclass
class ModelVersion:
    version_id: str
    model_name: str
    stage: VersionStage
    metrics: VersionMetrics
    created_at: str
    parent_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    changelog: List[str] = field(default_factory=list)
    is_active: bool = False


class VersioningEngine:
    """Model versioning and lifecycle management."""

    def __init__(self, max_versions: int = 50):
        self._versions: OrderedDict[str, ModelVersion] = OrderedDict()
        self._max_versions = max_versions
        self._active_prod: Optional[str] = None

    def register(self, version: ModelVersion) -> None:
        if len(self._versions) >= self._max_versions:
            self._versions.popitem(last=False)
        self._versions[version.version_id] = version
        logger.info(f"Registered {version.model_name} v{version.version_id}")

    def get(self, version_id: str) -> Optional[ModelVersion]:
        return self._versions.get(version_id)

    def promote(self, version_id: str, to_stage: VersionStage) -> bool:
        v = self._versions.get(version_id)
        if not v:
            return False
        old_stage = v.stage
        v.stage = to_stage
        v.changelog.append(f"Promoted: {old_stage.value} → {to_stage.value}")
        if to_stage == VersionStage.PROD:
            if self._active_prod:
                old = self._versions.get(self._active_prod)
                if old:
                    old.is_active = False
            v.is_active = True
            self._active_prod = version_id
        logger.info(f"Promoted {version_id}: {old_stage.value} → {to_stage.value}")
        return True

    def rollback(self, target_version_id: Optional[str] = None) -> Optional[ModelVersion]:
        if target_version_id:
            v = self._versions.get(target_version_id)
            if v:
                self.promote(target_version_id, VersionStage.PROD)
                v.changelog.append("Rolled back to this version")
                return v
        # Rollback to previous prod
        prod_versions = [v for v in self._versions.values() if v.stage == VersionStage.PROD or v.is_active]
        if len(prod_versions) >= 2:
            prev = prod_versions[-2]
            self.promote(prev.version_id, VersionStage.PROD)
            prev.changelog.append("Auto-rollback to previous production version")
            return prev
        return None

    def compare(self, v1_id: str, v2_id: str) -> Dict[str, Any]:
        a = self._versions.get(v1_id)
        b = self._versions.get(v2_id)
        if not a or not b:
            return {"error": "Version not found"}
        return {
            "version_a": v1_id,
            "version_b": v2_id,
            "accuracy_diff": b.metrics.accuracy - a.metrics.accuracy,
            "latency_diff_ms": b.metrics.latency_ms - a.metrics.latency_ms,
            "size_diff_mb": b.metrics.size_mb - a.metrics.size_mb,
            "perplexity_diff": b.metrics.perplexity - a.metrics.perplexity,
            "stage": (a.stage.value, b.stage.value),
        }

    def generate_changelog(self, from_version: Optional[str] = None, to_version: Optional[str] = None) -> List[str]:
        versions = list(self._versions.values())
        if from_version and to_version:
            versions = [v for v in versions if v.version_id >= from_version and v.version_id <= to_version]
        lines = [f"## Changelog ({len(versions)} versions)"]
        for v in versions:
            lines.append(f"### {v.version_id} [{v.stage.value}]")
            for entry in v.changelog:
                lines.append(f"- {entry}")
        return lines

    def list_versions(self, model_name: Optional[str] = None, stage: Optional[VersionStage] = None) -> List[ModelVersion]:
        result = list(self._versions.values())
        if model_name:
            result = [v for v in result if v.model_name == model_name]
        if stage:
            result = [v for v in result if v.stage == stage]
        return result

    def get_active_prod(self) -> Optional[ModelVersion]:
        if self._active_prod:
            return self._versions.get(self._active_prod)
        return None

    def get_stats(self) -> Dict[str, Any]:
        stages = {}
        for v in self._versions.values():
            stages[v.stage.value] = stages.get(v.stage.value, 0) + 1
        return {
            "total_versions": len(self._versions),
            "active_prod": self._active_prod,
            "by_stage": stages,
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Model Versioning Engine")
    print("ai/llm_versioning_engine_native.py")
    print("=" * 60)

    engine = VersioningEngine()

    # 1. Register versions
    print("[1] Register Versions")
    v1 = ModelVersion("1.0.0", "arena-model", VersionStage.DEV, VersionMetrics(0.82, 120, 500), "2025-01-01", tags=["baseline"])
    v2 = ModelVersion("1.1.0", "arena-model", VersionStage.DEV, VersionMetrics(0.85, 110, 510), "2025-02-01", parent_version="1.0.0", tags=["improved"])
    v3 = ModelVersion("1.2.0", "arena-model", VersionStage.STAGING, VersionMetrics(0.87, 105, 515), "2025-03-01", parent_version="1.1.0", tags=["stable"])
    v4 = ModelVersion("2.0.0", "arena-model", VersionStage.PROD, VersionMetrics(0.89, 95, 520), "2025-04-01", tags=["major"])
    for v in [v1, v2, v3, v4]:
        engine.register(v)
    print(f"  Registered 4 versions")

    # 2. Promote
    print("[2] Promote to Production")
    engine.promote("1.2.0", VersionStage.PROD)
    active = engine.get_active_prod()
    print(f"  Active prod: {active.version_id if active else 'None'}")

    # 3. Rollback
    print("[3] Rollback")
    rolled = engine.rollback("1.1.0")
    print(f"  Rolled back to: {rolled.version_id if rolled else 'None'}")
    active = engine.get_active_prod()
    print(f"  Active prod after rollback: {active.version_id if active else 'None'}")

    # 4. Compare
    print("[4] Compare Versions")
    diff = engine.compare("1.0.0", "2.0.0")
    print(f"  Accuracy diff: {diff['accuracy_diff']:+.3f}")
    print(f"  Latency diff: {diff['latency_diff_ms']:+.1f}ms")

    # 5. Changelog
    print("[5] Changelog")
    log = engine.generate_changelog()
    for line in log[:6]:
        print(f"  {line}")

    # 6. Stats
    print("[6] Engine Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
