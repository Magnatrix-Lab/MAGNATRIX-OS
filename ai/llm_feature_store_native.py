"""
llm_feature_store_native.py
MAGNATRIX-OS Feature Store Engine
Native Python, stdlib only.
Provides feature storage with online/offline serving, versioning, point-in-time correctness,
and feature validation for ML pipelines within MAGNATRIX-OS.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union


class FeatureType(Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BINARY = "binary"
    TEXT = "text"
    TIMESTAMP = "timestamp"
    EMBEDDING = "embedding"


class FeatureServingMode(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BOTH = "both"


@dataclass
class Feature:
    name: str
    feature_type: FeatureType
    description: str
    default_value: Any = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "feature_type": self.feature_type.value,
            "description": self.description, "default_value": self.default_value,
            "tags": self.tags, "metadata": self.metadata,
        }


@dataclass
class FeatureValue:
    entity_id: str
    feature_name: str
    value: Any
    timestamp: float
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id, "feature_name": self.feature_name,
            "value": self.value, "timestamp": self.timestamp,
            "version": self.version, "metadata": self.metadata,
        }


@dataclass
class FeatureSet:
    name: str
    features: List[Feature]
    serving_mode: FeatureServingMode = FeatureServingMode.BOTH
    owner: str = ""
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "features": [f.to_dict() for f in self.features],
            "serving_mode": self.serving_mode.value, "owner": self.owner,
            "version": self.version, "tags": self.tags, "created_at": self.created_at,
        }


class FeatureStoreEngine:
    """
    Feature store with online/offline serving, point-in-time correctness, and validation.
    """

    def __init__(self) -> None:
        self._feature_sets: Dict[str, FeatureSet] = {}
        self._online_store: Dict[str, Dict[str, FeatureValue]] = {}  # entity_id -> {feature_name: value}
        self._offline_store: Dict[str, List[FeatureValue]] = {}  # entity_id -> [values]
        self._feature_registry: Dict[str, Feature] = {}  # feature_name -> Feature
        self._validations: Dict[str, List[Callable]] = {}  # feature_name -> validators

    def register_feature_set(self, feature_set: FeatureSet) -> None:
        self._feature_sets[feature_set.name] = feature_set
        for f in feature_set.features:
            self._feature_registry[f.name] = f

    def register_feature(self, feature: Feature) -> None:
        self._feature_registry[feature.name] = feature

    def add_validator(self, feature_name: str, validator: Callable[[Any], bool]) -> None:
        self._validations.setdefault(feature_name, []).append(validator)

    def _validate(self, feature_name: str, value: Any) -> bool:
        validators = self._validations.get(feature_name, [])
        if not validators:
            return True
        return all(v(value) for v in validators)

    def write_online(self, entity_id: str, feature_name: str, value: Any,
                     timestamp: Optional[float] = None, version: str = "1.0") -> bool:
        if not self._validate(feature_name, value):
            return False
        ts = timestamp if timestamp is not None else time.time()
        fv = FeatureValue(entity_id=entity_id, feature_name=feature_name, value=value, timestamp=ts, version=version)
        if entity_id not in self._online_store:
            self._online_store[entity_id] = {}
        self._online_store[entity_id][feature_name] = fv
        return True

    def write_offline(self, entity_id: str, feature_name: str, value: Any,
                      timestamp: Optional[float] = None, version: str = "1.0") -> bool:
        if not self._validate(feature_name, value):
            return False
        ts = timestamp if timestamp is not None else time.time()
        fv = FeatureValue(entity_id=entity_id, feature_name=feature_name, value=value, timestamp=ts, version=version)
        if entity_id not in self._offline_store:
            self._offline_store[entity_id] = []
        self._offline_store[entity_id].append(fv)
        return True

    def write(self, entity_id: str, feature_name: str, value: Any,
              timestamp: Optional[float] = None, version: str = "1.0",
              serving_mode: FeatureServingMode = FeatureServingMode.BOTH) -> bool:
        if serving_mode in (FeatureServingMode.ONLINE, FeatureServingMode.BOTH):
            if not self.write_online(entity_id, feature_name, value, timestamp, version):
                return False
        if serving_mode in (FeatureServingMode.OFFLINE, FeatureServingMode.BOTH):
            if not self.write_offline(entity_id, feature_name, value, timestamp, version):
                return False
        return True

    def read_online(self, entity_id: str, feature_name: str) -> Optional[FeatureValue]:
        return self._online_store.get(entity_id, {}).get(feature_name)

    def read_offline(self, entity_id: str, feature_name: str, timestamp: float) -> Optional[FeatureValue]:
        values = self._offline_store.get(entity_id, [])
        candidates = [v for v in values if v.feature_name == feature_name and v.timestamp <= timestamp]
        if not candidates:
            return None
        return max(candidates, key=lambda v: v.timestamp)

    def read(self, entity_id: str, feature_name: str, timestamp: Optional[float] = None) -> Optional[FeatureValue]:
        if timestamp is not None:
            return self.read_offline(entity_id, feature_name, timestamp)
        return self.read_online(entity_id, feature_name)

    def get_entity_features(self, entity_id: str) -> Dict[str, Any]:
        online = self._online_store.get(entity_id, {})
        return {k: v.value for k, v in online.items()}

    def get_feature_vector(self, entity_ids: List[str], feature_names: List[str],
                           timestamp: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for eid in entity_ids:
            result[eid] = {}
            for fname in feature_names:
                fv = self.read(eid, fname, timestamp)
                result[eid][fname] = fv.value if fv else None
        return result

    def list_feature_sets(self) -> List[FeatureSet]:
        return list(self._feature_sets.values())

    def get_feature_set(self, name: str) -> Optional[FeatureSet]:
        return self._feature_sets.get(name)

    def get_feature(self, name: str) -> Optional[Feature]:
        return self._feature_registry.get(name)

    def stats(self) -> Dict[str, Any]:
        online_entities = len(self._online_store)
        offline_entities = len(self._offline_store)
        total_online = sum(len(v) for v in self._online_store.values())
        total_offline = sum(len(v) for v in self._offline_store.values())
        return {
            "feature_sets": len(self._feature_sets),
            "registered_features": len(self._feature_registry),
            "online_entities": online_entities,
            "offline_entities": offline_entities,
            "total_online_values": total_online,
            "total_offline_values": total_offline,
        }

    def export_feature_set(self, name: str, path: str) -> None:
        fs = self._feature_sets.get(name)
        if not fs:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fs.to_dict(), f, indent=2, default=str)

    def clear(self, entity_id: Optional[str] = None) -> None:
        if entity_id:
            self._online_store.pop(entity_id, None)
            self._offline_store.pop(entity_id, None)
        else:
            self._online_store.clear()
            self._offline_store.clear()


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Feature Store Engine")
    print("=" * 60)

    store = FeatureStoreEngine()

    # Define feature set
    customer_features = FeatureSet(
        name="customer_churn", serving_mode=FeatureServingMode.BOTH, owner="ml_team",
        features=[
            Feature("age", FeatureType.NUMERIC, "Customer age", default_value=0, tags=["demographic"]),
            Feature("tenure_months", FeatureType.NUMERIC, "Months as customer", default_value=0, tags=["behavior"]),
            Feature("contract_type", FeatureType.CATEGORICAL, "Contract type", default_value="monthly", tags=["demographic"]),
            Feature("monthly_charges", FeatureType.NUMERIC, "Monthly bill amount", default_value=0.0, tags=["billing"]),
            Feature("total_charges", FeatureType.NUMERIC, "Total bill amount", default_value=0.0, tags=["billing"]),
        ],
        tags=["churn_prediction", "core"]
    )
    store.register_feature_set(customer_features)

    # Add validators
    store.add_validator("age", lambda v: isinstance(v, (int, float)) and 0 <= v <= 120)
    store.add_validator("monthly_charges", lambda v: isinstance(v, (int, float)) and v >= 0)

    print("\n--- Writing features ---")
    store.write("cust_001", "age", 35, serving_mode=FeatureServingMode.BOTH)
    store.write("cust_001", "tenure_months", 24, serving_mode=FeatureServingMode.BOTH)
    store.write("cust_001", "contract_type", "annual", serving_mode=FeatureServingMode.BOTH)
    store.write("cust_001", "monthly_charges", 79.99, serving_mode=FeatureServingMode.BOTH)
    store.write("cust_001", "total_charges", 1919.76, serving_mode=FeatureServingMode.BOTH)

    store.write("cust_002", "age", 42, serving_mode=FeatureServingMode.BOTH)
    store.write("cust_002", "tenure_months", 12, serving_mode=FeatureServingMode.BOTH)
    store.write("cust_002", "contract_type", "monthly", serving_mode=FeatureServingMode.BOTH)
    store.write("cust_002", "monthly_charges", 55.00, serving_mode=FeatureServingMode.BOTH)

    # Invalid write (negative charges)
    ok = store.write("cust_003", "monthly_charges", -10.0)
    print(f"  Invalid write rejected: {not ok}")

    print("\n--- Online read ---")
    fv = store.read_online("cust_001", "age")
    print(f"  cust_001 age: {fv.value if fv else 'N/A'}")

    print("\n--- Entity features ---")
    features = store.get_entity_features("cust_001")
    for k, v in features.items():
        print(f"  {k}: {v}")

    print("\n--- Feature vector ---")
    vector = store.get_feature_vector(["cust_001", "cust_002"], ["age", "tenure_months", "contract_type"])
    for eid, feats in vector.items():
        print(f"  {eid}: {feats}")

    print("\n--- Point-in-time read ---")
    t1 = time.time()
    store.write("cust_001", "monthly_charges", 89.99, timestamp=t1)
    time.sleep(0.1)
    t2 = time.time()
    store.write("cust_001", "monthly_charges", 99.99, timestamp=t2)
    # Read at t1 (should get 89.99)
    pit = store.read_offline("cust_001", "monthly_charges", t1 + 0.05)
    print(f"  Point-in-time at t1+0.05: {pit.value if pit else 'N/A'}")
    # Read at t2 (should get 99.99)
    pit2 = store.read_offline("cust_001", "monthly_charges", t2 + 0.05)
    print(f"  Point-in-time at t2+0.05: {pit2.value if pit2 else 'N/A'}")

    print("\n--- Stats ---")
    print(store.stats())

    print("\nFeature Store test complete.")


if __name__ == "__main__":
    run()
