#!/usr/bin/env python3
"""Feature Store for MAGNATRIX-OS — Manage ML features for training."""
from __future__ import annotations
import json, time, threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class Feature:
    name: str
    dtype: str = "float"
    source: str = ""
    transform: str = "identity"
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

class FeatureStore:
    def __init__(self, store_dir: str = "./data/features") -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._features: Dict[str, Feature] = {}
        self._values: Dict[str, List[Any]] = {}
        self._lock = threading.Lock()

    def register(self, feature: Feature) -> None:
        with self._lock:
            self._features[feature.name] = feature

    def ingest(self, feature_name: str, value: Any, timestamp: Optional[float] = None) -> None:
        with self._lock:
            if feature_name not in self._values:
                self._values[feature_name] = []
            self._values[feature_name].append({"value": value, "ts": timestamp or time.time()})

    def get_feature_vector(self, feature_names: List[str]) -> Dict[str, Any]:
        with self._lock:
            return {n: self._values.get(n, [])[-1]["value"] if self._values.get(n) else None for n in feature_names}

    def save(self) -> str:
        data = {
            "features": {k: v.__dict__ for k, v in self._features.items()},
            "values": {k: v[-1000:] for k, v in self._values.items()},
        }
        path = self.store_dir / "store.json"
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return str(path)

    def list_features(self) -> List[str]:
        return list(self._features.keys())

    def stats(self) -> Dict[str, Any]:
        return {"features": len(self._features), "total_values": sum(len(v) for v in self._values.values())}
