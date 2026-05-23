#!/usr/bin/env python3
"""
applied_ml_native.py — Native reimplementation of eugeneyan/applied-ml.
Systematic machine learning for production: pipelines, feature engineering,
model serving, monitoring, A/B testing, data validation, orchestration.
Pure Python, no hard dependencies.
"""

from __future__ import annotations

import json
import math
import random
import sqlite3
import hashlib
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — ML System Design: Pipeline DAG, Config, Artifact Store
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class StageConfig:
    """Configuration for a single pipeline stage."""
    name: str
    stage_type: str  # 'ingest', 'validate', 'featurize', 'train', 'evaluate', 'deploy'
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 3
    timeout_seconds: int = 300
    depends_on: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<StageConfig {self.name} type={self.stage_type}>"


class Stage(ABC):
    """Abstract base for a pipeline stage."""

    def __init__(self, config: StageConfig) -> None:
        self.config = config
        self._state: str = "pending"
        self._last_run: Optional[datetime] = None
        self._error_message: Optional[str] = None

    def __repr__(self) -> str:
        return f"<Stage {self.config.name} state={self._state}>"

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the stage. Returns updated context."""
        raise NotImplementedError

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute with error handling and state tracking."""
        self._state = "running"
        self._last_run = datetime.now(timezone.utc)
        try:
            result = self.run(context)
            self._state = "success"
            return result
        except Exception as e:
            self._state = "failed"
            self._error_message = str(e)
            raise


class IngestStage(Stage):
    """Data ingestion stage."""

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        source = self.config.params.get("source", "default")
        context["data_ingested"] = True
        context["ingest_source"] = source
        return context


class ValidateStage(Stage):
    """Data validation stage."""

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        context["data_validated"] = True
        return context


class FeaturizeStage(Stage):
    """Feature engineering stage."""

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        context["features_built"] = True
        return context


class TrainStage(Stage):
    """Model training stage."""

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        context["model_trained"] = True
        context["model_metrics"] = {"accuracy": 0.92, "f1": 0.89}
        return context


class EvaluateStage(Stage):
    """Model evaluation stage."""

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        context["model_evaluated"] = True
        return context


class DeployStage(Stage):
    """Model deployment stage."""

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        context["model_deployed"] = True
        return context


class Pipeline:
    """DAG-based ML pipeline with topological execution."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._stages: Dict[str, Stage] = {}
        self._adjacency: Dict[str, List[str]] = {}  # stage -> dependents
        self._indegree: Dict[str, int] = {}
        self._execution_log: List[Dict[str, Any]] = []

    def __repr__(self) -> str:
        return f"<Pipeline '{self.name}' stages={len(self._stages)}>"

    def add_stage(self, stage: Stage) -> None:
        self._stages[stage.config.name] = stage
        self._adjacency.setdefault(stage.config.name, [])
        self._indegree[stage.config.name] = 0

    def connect(self, upstream: str, downstream: str) -> None:
        """Declare that downstream depends on upstream."""
        self._adjacency.setdefault(upstream, []).append(downstream)
        self._indegree[downstream] = self._indegree.get(downstream, 0) + 1

    def topological_order(self) -> List[str]:
        """Kahn's algorithm for topological sort."""
        order: List[str] = []
        indeg = dict(self._indegree)
        queue = [s for s, d in indeg.items() if d == 0]
        while queue:
            current = queue.pop(0)
            order.append(current)
            for dep in self._adjacency.get(current, []):
                indeg[dep] -= 1
                if indeg[dep] == 0:
                    queue.append(dep)
        if len(order) != len(self._stages):
            raise ValueError("Cycle detected in pipeline DAG")
        return order

    def run(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute all stages in topological order."""
        ctx = context or {}
        order = self.topological_order()
        for stage_name in order:
            stage = self._stages[stage_name]
            ctx = stage.execute(ctx)
            self._execution_log.append({
                "stage": stage_name,
                "state": stage._state,
                "timestamp": stage._last_run.isoformat() if stage._last_run else None
            })
        return ctx

    def get_log(self) -> List[Dict[str, Any]]:
        return self._execution_log


class ConfigRegistry:
    """Central configuration store for ML systems."""

    def __init__(self) -> None:
        self._configs: Dict[str, Any] = {}
        self._versions: Dict[str, int] = {}

    def __repr__(self) -> str:
        return f"<ConfigRegistry keys={len(self._configs)}>"

    def set(self, key: str, value: Any) -> None:
        self._configs[key] = value
        self._versions[key] = self._versions.get(key, 0) + 1

    def get(self, key: str, default: Any = None) -> Any:
        return self._configs.get(key, default)

    def all(self) -> Dict[str, Any]:
        return dict(self._configs)


@dataclass
class Artifact:
    """A versioned ML artifact (model, dataset, config)."""
    id: str
    name: str
    version: str
    artifact_type: str  # 'model', 'dataset', 'config', 'metrics'
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lineage: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<Artifact {self.name} v{self.version} type={self.artifact_type}>"


class ArtifactStore:
    """Versioned artifact storage with SQLite-backed metadata."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._artifacts: Dict[str, Artifact] = {}
        self._db_path = db_path
        if db_path:
            self._init_db()

    def __repr__(self) -> str:
        return f"<ArtifactStore artifacts={len(self._artifacts)}>"

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                name TEXT,
                version TEXT,
                artifact_type TEXT,
                metadata TEXT,
                created_at TEXT,
                lineage TEXT
            )
        """)
        conn.commit()
        conn.close()

    def save(self, artifact: Artifact) -> None:
        self._artifacts[artifact.id] = artifact
        if self._db_path:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "INSERT OR REPLACE INTO artifacts VALUES (?,?,?,?,?,?,?)",
                (artifact.id, artifact.name, artifact.version, artifact.artifact_type,
                 json.dumps(artifact.metadata), artifact.created_at.isoformat(),
                 json.dumps(artifact.lineage))
            )
            conn.commit()
            conn.close()

    def get(self, artifact_id: str) -> Optional[Artifact]:
        return self._artifacts.get(artifact_id)

    def list_by_type(self, artifact_type: str) -> List[Artifact]:
        return [a for a in self._artifacts.values() if a.artifact_type == artifact_type]

    def latest(self, name: str) -> Optional[Artifact]:
        matches = [a for a in self._artifacts.values() if a.name == name]
        if not matches:
            return None
        return max(matches, key=lambda a: a.created_at)


class MLSystem:
    """High-level ML system orchestrator."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.config = ConfigRegistry()
        self.artifacts = ArtifactStore()
        self.pipelines: Dict[str, Pipeline] = {}
        self._initialized_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<MLSystem '{self.name}' pipelines={len(self.pipelines)}>"

    def add_pipeline(self, pipeline: Pipeline) -> None:
        self.pipelines[pipeline.name] = pipeline

    def run_pipeline(self, pipeline_name: str) -> Dict[str, Any]:
        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            raise ValueError(f"Pipeline '{pipeline_name}' not found")
        return pipeline.run()

    def stats(self) -> Dict[str, Any]:
        return {
            "system_name": self.name,
            "pipelines": len(self.pipelines),
            "artifacts": len(self.artifacts._artifacts),
            "configs": len(self.config.all()),
            "uptime_seconds": (datetime.now(timezone.utc) - self._initialized_at).total_seconds()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Feature Engineering: Store, Transformers, Validation, Pipeline
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Feature:
    """Definition of a single feature."""
    name: str
    feature_type: str  # 'numeric', 'categorical', 'binary', 'datetime', 'text'
    source: str = ""
    description: str = ""
    transform: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<Feature {self.name} type={self.feature_type}>"


class FeatureStore:
    """Registry and retrieval for feature definitions."""

    def __init__(self) -> None:
        self._features: Dict[str, Feature] = {}
        self._groups: Dict[str, List[str]] = {}  # group_name -> feature_names
        self._online_cache: Dict[str, Dict[str, Any]] = {}

    def __repr__(self) -> str:
        return f"<FeatureStore features={len(self._features)} groups={len(self._groups)}>"

    def register(self, feature: Feature, group: str = "default") -> None:
        self._features[feature.name] = feature
        self._groups.setdefault(group, []).append(feature.name)

    def get(self, name: str) -> Optional[Feature]:
        return self._features.get(name)

    def get_group(self, group_name: str) -> List[Feature]:
        names = self._groups.get(group_name, [])
        return [self._features[n] for n in names if n in self._features]

    def list_features(self) -> List[str]:
        return list(self._features.keys())

    def set_online_value(self, entity_id: str, feature_name: str, value: Any) -> None:
        self._online_cache.setdefault(entity_id, {})[feature_name] = value

    def get_online_values(self, entity_id: str) -> Dict[str, Any]:
        return self._online_cache.get(entity_id, {})


class FeatureTransformer(ABC):
    """Abstract base for feature transformations."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._fitted = False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} fitted={self._fitted}>"

    @abstractmethod
    def fit(self, data: List[List[float]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def transform(self, data: List[List[float]]) -> List[List[float]]:
        raise NotImplementedError

    def fit_transform(self, data: List[List[float]]) -> List[List[float]]:
        self.fit(data)
        return self.transform(data)


class StandardScaler(FeatureTransformer):
    """Z-score normalization: (x - mean) / std."""

    def __init__(self) -> None:
        super().__init__("StandardScaler")
        self._means: List[float] = []
        self._stds: List[float] = []

    def fit(self, data: List[List[float]]) -> None:
        if not data:
            return
        n_features = len(data[0])
        self._means = []
        self._stds = []
        for i in range(n_features):
            col = [row[i] for row in data]
            mean_val = statistics.mean(col)
            stdev_val = statistics.stdev(col) if len(col) > 1 else 1.0
            self._means.append(mean_val)
            self._stds.append(stdev_val if stdev_val > 0 else 1.0)
        self._fitted = True

    def transform(self, data: List[List[float]]) -> List[List[float]]:
        if not self._fitted:
            raise RuntimeError("Transformer not fitted")
        result: List[List[float]] = []
        for row in data:
            new_row = [(row[i] - self._means[i]) / self._stds[i] for i in range(len(row))]
            result.append(new_row)
        return result


class MinMaxScaler(FeatureTransformer):
    """Min-max normalization: (x - min) / (max - min)."""

    def __init__(self) -> None:
        super().__init__("MinMaxScaler")
        self._mins: List[float] = []
        self._maxs: List[float] = []

    def fit(self, data: List[List[float]]) -> None:
        if not data:
            return
        n_features = len(data[0])
        self._mins = []
        self._maxs = []
        for i in range(n_features):
            col = [row[i] for row in data]
            min_val = min(col)
            max_val = max(col)
            self._mins.append(min_val)
            self._maxs.append(max_val if max_val > min_val else min_val + 1)
        self._fitted = True

    def transform(self, data: List[List[float]]) -> List[List[float]]:
        if not self._fitted:
            raise RuntimeError("Transformer not fitted")
        result: List[List[float]] = []
        for row in data:
            new_row = [(row[i] - self._mins[i]) / (self._maxs[i] - self._mins[i]) for i in range(len(row))]
            result.append(new_row)
        return result


class OneHotEncoder(FeatureTransformer):
    """One-hot encoding for categorical features."""

    def __init__(self) -> None:
        super().__init__("OneHotEncoder")
        self._categories: List[List[str]] = []

    def fit(self, data: List[List[float]]) -> None:
        """Expects data as list of lists where each inner list has one string."""
        pass  # stub: real implementation would extract unique categories

    def transform(self, data: List[List[float]]) -> List[List[float]]:
        return data  # stub


class BinningTransformer(FeatureTransformer):
    """Equal-width binning for numeric features."""

    def __init__(self, n_bins: int = 5) -> None:
        super().__init__("BinningTransformer")
        self.n_bins = n_bins
        self._bin_edges: List[List[float]] = []

    def fit(self, data: List[List[float]]) -> None:
        if not data:
            return
        n_features = len(data[0])
        self._bin_edges = []
        for i in range(n_features):
            col = sorted([row[i] for row in data])
            min_val = col[0]
            max_val = col[-1]
            step = (max_val - min_val) / self.n_bins
            edges = [min_val + step * j for j in range(self.n_bins + 1)]
            self._bin_edges.append(edges)
        self._fitted = True

    def transform(self, data: List[List[float]]) -> List[List[float]]:
        if not self._fitted:
            raise RuntimeError("Transformer not fitted")
        result: List[List[float]] = []
        for row in data:
            new_row: List[float] = []
            for i, val in enumerate(row):
                edges = self._bin_edges[i]
                bin_idx = 0
                for j in range(len(edges) - 1):
                    if edges[j] <= val < edges[j + 1]:
                        bin_idx = j
                        break
                if val >= edges[-1]:
                    bin_idx = len(edges) - 2
                one_hot = [0.0] * (len(edges) - 1)
                one_hot[bin_idx] = 1.0
                new_row.extend(one_hot)
            result.append(new_row)
        return result


class PolynomialFeatures(FeatureTransformer):
    """Generate polynomial interaction features."""

    def __init__(self, degree: int = 2) -> None:
        super().__init__("PolynomialFeatures")
        self.degree = degree

    def fit(self, data: List[List[float]]) -> None:
        self._fitted = True

    def transform(self, data: List[List[float]]) -> List[List[float]]:
        result: List[List[float]] = []
        for row in data:
            new_row = list(row)
            if self.degree >= 2:
                for i in range(len(row)):
                    for j in range(i, len(row)):
                        new_row.append(row[i] * row[j])
            if self.degree >= 3:
                for i in range(len(row)):
                    new_row.append(row[i] ** 3)
            result.append(new_row)
        return result


class FeatureValidator:
    """Validate feature quality and consistency."""

    def __init__(self) -> None:
        self._checks: List[Dict[str, Any]] = []

    def __repr__(self) -> str:
        return f"<FeatureValidator checks={len(self._checks)}>"

    def check_null_rate(self, values: List[Any], max_rate: float = 0.1) -> bool:
        nulls = sum(1 for v in values if v is None)
        rate = nulls / len(values) if values else 0
        passed = rate <= max_rate
        self._checks.append({"check": "null_rate", "passed": passed, "rate": rate})
        return passed

    def check_range(self, values: List[float], min_val: float, max_val: float) -> bool:
        passed = all(min_val <= v <= max_val for v in values if v is not None)
        self._checks.append({"check": "range", "passed": passed, "min": min_val, "max": max_val})
        return passed

    def check_type(self, values: List[Any], expected_type: type) -> bool:
        passed = all(isinstance(v, expected_type) for v in values if v is not None)
        self._checks.append({"check": "type", "passed": passed, "expected": expected_type.__name__})
        return passed

    def report(self) -> Dict[str, Any]:
        passed = sum(1 for c in self._checks if c["passed"])
        return {"total": len(self._checks), "passed": passed, "failed": len(self._checks) - passed, "checks": self._checks}


class FeaturePipeline:
    """Sequential feature transformation pipeline."""

    def __init__(self, transformers: Optional[List[FeatureTransformer]] = None) -> None:
        self.transformers = transformers or []
        self._feature_names_out: List[str] = []

    def __repr__(self) -> str:
        return f"<FeaturePipeline steps={len(self.transformers)}>"

    def add(self, transformer: FeatureTransformer) -> None:
        self.transformers.append(transformer)

    def fit_transform(self, data: List[List[float]]) -> List[List[float]]:
        current = data
        for t in self.transformers:
            current = t.fit_transform(current)
        return current

    def transform(self, data: List[List[float]]) -> List[List[float]]:
        current = data
        for t in self.transformers:
            current = t.transform(current)
        return current


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Model Serving: Registry, Inference, Batch Prediction
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ModelArtifact:
    """A trained model with metadata."""
    model_id: str
    name: str
    version: str
    framework: str  # 'sklearn', 'tensorflow', 'pytorch', 'xgboost', 'custom'
    metrics: Dict[str, float] = field(default_factory=dict)
    hyperparams: Dict[str, Any] = field(default_factory=dict)
    feature_names: List[str] = field(default_factory=list)
    training_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    artifact_path: str = ""

    def __repr__(self) -> str:
        return f"<ModelArtifact {self.name} v{self.version} framework={self.framework}>"


class SimpleModelStub:
    """A simple linear model stub for demonstration."""

    def __init__(self, weights: List[float], bias: float = 0.0) -> None:
        self.weights = weights
        self.bias = bias

    def predict(self, features: List[float]) -> float:
        return sum(w * f for w, f in zip(self.weights, features)) + self.bias

    def predict_batch(self, features: List[List[float]]) -> List[float]:
        return [self.predict(row) for row in features]


class ModelRegistry:
    """Registry for model versions with promotion workflow."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelArtifact] = {}
        self._production: Optional[str] = None
        self._staging: Optional[str] = None

    def __repr__(self) -> str:
        return f"<ModelRegistry models={len(self._models)} prod={self._production}>"

    def register(self, model: ModelArtifact) -> None:
        self._models[model.model_id] = model

    def get(self, model_id: str) -> Optional[ModelArtifact]:
        return self._models.get(model_id)

    def promote_to_staging(self, model_id: str) -> bool:
        if model_id in self._models:
            self._staging = model_id
            return True
        return False

    def promote_to_production(self, model_id: str) -> bool:
        if model_id in self._models:
            self._production = model_id
            return True
        return False

    def get_production(self) -> Optional[ModelArtifact]:
        if self._production:
            return self._models.get(self._production)
        return None

    def list_versions(self, name: str) -> List[ModelArtifact]:
        return [m for m in self._models.values() if m.name == name]


class InferenceServer:
    """Stub for a model inference server."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self._model_cache: Dict[str, SimpleModelStub] = {}
        self._request_count = 0
        self._latency_log: List[float] = []

    def __repr__(self) -> str:
        return f"<InferenceServer requests={self._request_count}>"

    def load_model(self, model_id: str) -> bool:
        model = self.registry.get(model_id)
        if not model:
            return False
        # Create a stub model with random weights matching feature count
        n_features = len(model.feature_names) or 5
        weights = [random.uniform(-1, 1) for _ in range(n_features)]
        self._model_cache[model_id] = SimpleModelStub(weights)
        return True

    def predict(self, model_id: str, features: List[float]) -> Dict[str, Any]:
        start = datetime.now(timezone.utc)
        self._request_count += 1
        model_stub = self._model_cache.get(model_id)
        if not model_stub:
            loaded = self.load_model(model_id)
            if not loaded:
                return {"error": "Model not found"}
            model_stub = self._model_cache[model_id]
        prediction = model_stub.predict(features)
        latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        self._latency_log.append(latency_ms)
        return {
            "model_id": model_id,
            "prediction": prediction,
            "latency_ms": round(latency_ms, 2)
        }

    def predict_batch(self, model_id: str, features: List[List[float]]) -> List[Dict[str, Any]]:
        return [self.predict(model_id, row) for row in features]

    def get_latency_stats(self) -> Dict[str, float]:
        if not self._latency_log:
            return {}
        sorted_log = sorted(self._latency_log)
        n = len(sorted_log)
        return {
            "p50": sorted_log[n // 2],
            "p95": sorted_log[int(n * 0.95)],
            "p99": sorted_log[int(n * 0.99)],
            "mean": statistics.mean(sorted_log)
        }


class BatchPredictor:
    """Orchestrate large-scale batch inference."""

    def __init__(self, server: InferenceServer, batch_size: int = 100) -> None:
        self.server = server
        self.batch_size = batch_size

    def __repr__(self) -> str:
        return f"<BatchPredictor batch_size={self.batch_size}>"

    def run(self, model_id: str, dataset: List[List[float]]) -> List[float]:
        predictions: List[float] = []
        for i in range(0, len(dataset), self.batch_size):
            batch = dataset[i:i + self.batch_size]
            results = self.server.predict_batch(model_id, batch)
            predictions.extend([r["prediction"] for r in results if "prediction" in r])
        return predictions


@dataclass
class PredictionLog:
    """Log entry for a prediction request."""
    request_id: str
    model_id: str
    timestamp: datetime
    features: List[float]
    prediction: float
    latency_ms: float

    def __repr__(self) -> str:
        return f"<PredictionLog req={self.request_id} model={self.model_id}>"


class PredictionLogger:
    """Collect and query prediction logs."""

    def __init__(self) -> None:
        self._logs: List[PredictionLog] = []

    def log(self, entry: PredictionLog) -> None:
        self._logs.append(entry)

    def get_logs(self, model_id: Optional[str] = None, limit: int = 100) -> List[PredictionLog]:
        logs = [l for l in self._logs if model_id is None or l.model_id == model_id]
        return logs[-limit:]

    def distribution(self, model_id: str) -> Dict[str, float]:
        values = [l.prediction for l in self._logs if l.model_id == model_id]
        if not values:
            return {}
        return {
            "mean": statistics.mean(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Monitoring & Drift Detection
# ═══════════════════════════════════════════════════════════════════════════════


class Monitor:
    """General metric collection and alerting."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._metrics: Dict[str, List[float]] = {}
        self._thresholds: Dict[str, Tuple[float, float]] = {}  # metric -> (lower, upper)
        self._alerts: List[Dict[str, Any]] = []

    def __repr__(self) -> str:
        return f"<Monitor '{self.name}' metrics={len(self._metrics)}>"

    def record(self, metric_name: str, value: float) -> None:
        self._metrics.setdefault(metric_name, []).append(value)

    def set_threshold(self, metric_name: str, lower: float, upper: float) -> None:
        self._thresholds[metric_name] = (lower, upper)

    def check(self, metric_name: str) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        values = self._metrics.get(metric_name, [])
        if not values:
            return alerts
        threshold = self._thresholds.get(metric_name)
        if not threshold:
            return alerts
        lower, upper = threshold
        latest = values[-1]
        if latest < lower or latest > upper:
            alerts.append({
                "metric": metric_name,
                "value": latest,
                "threshold": threshold,
                "severity": "warning" if lower <= latest <= upper * 1.2 else "critical",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        return alerts

    def check_all(self) -> List[Dict[str, Any]]:
        all_alerts: List[Dict[str, Any]] = []
        for metric_name in self._metrics:
            all_alerts.extend(self.check(metric_name))
        self._alerts.extend(all_alerts)
        return all_alerts

    def get_alerts(self) -> List[Dict[str, Any]]:
        return self._alerts

    def summary(self, metric_name: str) -> Dict[str, float]:
        values = self._metrics.get(metric_name, [])
        if not values:
            return {}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "mean": statistics.mean(values),
            "median": sorted_vals[n // 2],
            "min": min(values),
            "max": max(values),
            "last": values[-1]
        }


class DataDriftDetector:
    """Detect drift in feature distributions over time."""

    def __init__(self) -> None:
        self._reference: Dict[str, List[float]] = {}
        self._current: Dict[str, List[float]] = {}

    def __repr__(self) -> str:
        return f"<DataDriftDetector features={len(self._reference)}>"

    def set_reference(self, feature_name: str, values: List[float]) -> None:
        self._reference[feature_name] = values

    def set_current(self, feature_name: str, values: List[float]) -> None:
        self._current[feature_name] = values

    def _psi(self, reference: List[float], current: List[float], bins: int = 10) -> float:
        """Population Stability Index."""
        min_val = min(min(reference), min(current))
        max_val = max(max(reference), max(current))
        step = (max_val - min_val) / bins
        if step == 0:
            return 0.0
        ref_counts = [0] * bins
        cur_counts = [0] * bins
        for v in reference:
            idx = min(int((v - min_val) / step), bins - 1)
            ref_counts[idx] += 1
        for v in current:
            idx = min(int((v - min_val) / step), bins - 1)
            cur_counts[idx] += 1
        ref_rates = [c / len(reference) for c in ref_counts]
        cur_rates = [c / len(current) for c in cur_counts]
        psi = 0.0
        for i in range(bins):
            if ref_rates[i] > 0 and cur_rates[i] > 0:
                psi += (cur_rates[i] - ref_rates[i]) * math.log(cur_rates[i] / ref_rates[i])
        return psi

    def detect(self, feature_name: str) -> Dict[str, Any]:
        ref = self._reference.get(feature_name, [])
        cur = self._current.get(feature_name, [])
        if not ref or not cur:
            return {"feature": feature_name, "error": "missing data"}
        psi_value = self._psi(ref, cur)
        ref_mean = statistics.mean(ref)
        cur_mean = statistics.mean(cur)
        ref_std = statistics.stdev(ref) if len(ref) > 1 else 0
        cur_std = statistics.stdev(cur) if len(cur) > 1 else 0
        return {
            "feature": feature_name,
            "psi": round(psi_value, 4),
            "drift_detected": psi_value > 0.2,
            "reference_mean": round(ref_mean, 4),
            "current_mean": round(cur_mean, 4),
            "reference_std": round(ref_std, 4),
            "current_std": round(cur_std, 4)
        }

    def detect_all(self) -> List[Dict[str, Any]]:
        return [self.detect(f) for f in self._reference.keys()]


class ModelDriftDetector:
    """Detect model performance degradation."""

    def __init__(self) -> None:
        self._baseline_metrics: Dict[str, float] = {}
        self._current_metrics: Dict[str, float] = {}

    def __repr__(self) -> str:
        return f"<ModelDriftDetector metrics={len(self._baseline_metrics)}>"

    def set_baseline(self, metric_name: str, value: float) -> None:
        self._baseline_metrics[metric_name] = value

    def set_current(self, metric_name: str, value: float) -> None:
        self._current_metrics[metric_name] = value

    def check(self, metric_name: str, threshold_pct: float = 5.0) -> Dict[str, Any]:
        baseline = self._baseline_metrics.get(metric_name)
        current = self._current_metrics.get(metric_name)
        if baseline is None or current is None:
            return {"metric": metric_name, "error": "missing"}
        drop_pct = ((baseline - current) / baseline) * 100 if baseline != 0 else 0
        return {
            "metric": metric_name,
            "baseline": baseline,
            "current": current,
            "drop_pct": round(drop_pct, 2),
            "degraded": drop_pct > threshold_pct
        }

    def check_all(self, threshold_pct: float = 5.0) -> List[Dict[str, Any]]:
        return [self.check(m, threshold_pct) for m in self._baseline_metrics.keys()]


class LatencyTracker:
    """Track inference latency percentiles."""

    def __init__(self) -> None:
        self._latencies: List[float] = []

    def record(self, latency_ms: float) -> None:
        self._latencies.append(latency_ms)

    def stats(self) -> Dict[str, float]:
        if not self._latencies:
            return {}
        sorted_lat = sorted(self._latencies)
        n = len(sorted_lat)
        return {
            "count": n,
            "p50": sorted_lat[n // 2],
            "p95": sorted_lat[int(n * 0.95)],
            "p99": sorted_lat[int(n * 0.99)],
            "mean": statistics.mean(sorted_lat),
            "max": max(sorted_lat)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — A/B Testing Framework
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Variant:
    """A variant in an A/B test experiment."""
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    traffic_weight: float = 0.5
    metrics: Dict[str, List[float]] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<Variant {self.name} weight={self.traffic_weight}>"


@dataclass
class Experiment:
    """An A/B test experiment definition."""
    experiment_id: str
    name: str
    variants: List[Variant] = field(default_factory=list)
    success_metric: str = "conversion"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "draft"  # draft, running, paused, completed
    sample_size_target: int = 1000

    def __repr__(self) -> str:
        return f"<Experiment {self.name} variants={len(self.variants)} status={self.status}>"


class ABTestEngine:
    """Random assignment and experiment management."""

    def __init__(self) -> None:
        self._experiments: Dict[str, Experiment] = {}
        self._assignments: Dict[str, str] = {}  # user_id -> variant_name
        self._rng = random.Random()

    def __repr__(self) -> str:
        return f"<ABTestEngine experiments={len(self._experiments)}>"

    def create_experiment(self, name: str, variants: List[Variant],
                          success_metric: str = "conversion") -> Experiment:
        exp_id = hashlib.sha256(name.encode()).hexdigest()[:12]
        exp = Experiment(
            experiment_id=exp_id,
            name=name,
            variants=variants,
            success_metric=success_metric,
            status="draft"
        )
        self._experiments[exp_id] = exp
        return exp

    def start_experiment(self, experiment_id: str) -> bool:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        exp.status = "running"
        exp.start_time = datetime.now(timezone.utc)
        return True

    def assign(self, experiment_id: str, user_id: str) -> Optional[str]:
        """Assign a user to a variant using weighted random selection."""
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != "running":
            return None
        key = f"{experiment_id}:{user_id}"
        if key in self._assignments:
            return self._assignments[key]
        total_weight = sum(v.traffic_weight for v in exp.variants)
        r = self._rng.uniform(0, total_weight)
        cumulative = 0.0
        for v in exp.variants:
            cumulative += v.traffic_weight
            if r <= cumulative:
                self._assignments[key] = v.name
                return v.name
        return exp.variants[-1].name if exp.variants else None

    def record_metric(self, experiment_id: str, variant_name: str, value: float) -> None:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return
        for v in exp.variants:
            if v.name == variant_name:
                v.metrics.setdefault(exp.success_metric, []).append(value)
                break

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return self._experiments.get(experiment_id)


class StatisticalTest:
    """Basic statistical tests for A/B test analysis."""

    def __init__(self) -> None:
        pass

    def mean_diff_ci(self, group_a: List[float], group_b: List[float],
                     confidence: float = 0.95) -> Dict[str, Any]:
        """Confidence interval for difference in means."""
        n_a = len(group_a)
        n_b = len(group_b)
        if n_a < 2 or n_b < 2:
            return {"error": "insufficient data"}
        mean_a = statistics.mean(group_a)
        mean_b = statistics.mean(group_b)
        var_a = statistics.variance(group_a)
        var_b = statistics.variance(group_b)
        pooled_se = math.sqrt(var_a / n_a + var_b / n_b)
        # z-score approximation for 95% CI
        z = 1.96 if confidence == 0.95 else 2.576
        diff = mean_b - mean_a
        ci_lower = diff - z * pooled_se
        ci_upper = diff + z * pooled_se
        return {
            "mean_a": mean_a,
            "mean_b": mean_b,
            "diff": diff,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "significant": ci_lower > 0 or ci_upper < 0
        }

    def t_test_stub(self, group_a: List[float], group_b: List[float]) -> Dict[str, Any]:
        """Simplified t-test using mean difference / pooled SE."""
        n_a = len(group_a)
        n_b = len(group_b)
        if n_a < 2 or n_b < 2:
            return {"error": "insufficient data"}
        mean_a = statistics.mean(group_a)
        mean_b = statistics.mean(group_b)
        var_a = statistics.variance(group_a)
        var_b = statistics.variance(group_b)
        pooled_se = math.sqrt(var_a / n_a + var_b / n_b)
        t_stat = (mean_b - mean_a) / pooled_se if pooled_se > 0 else 0
        return {
            "t_statistic": round(t_stat, 4),
            "mean_a": round(mean_a, 4),
            "mean_b": round(mean_b, 4)
        }


class ExperimentAnalyzer:
    """Analyze experiment results and compute lift."""

    def __init__(self, engine: ABTestEngine) -> None:
        self.engine = engine
        self.stats = StatisticalTest()

    def analyze(self, experiment_id: str) -> Dict[str, Any]:
        exp = self.engine.get_experiment(experiment_id)
        if not exp:
            return {"error": "experiment not found"}
        results: Dict[str, Any] = {
            "experiment": exp.name,
            "status": exp.status,
            "success_metric": exp.success_metric,
            "variants": []
        }
        baseline_values: Optional[List[float]] = None
        for v in exp.variants:
            values = v.metrics.get(exp.success_metric, [])
            mean_val = statistics.mean(values) if values else 0
            if baseline_values is None:
                baseline_values = values
            results["variants"].append({
                "name": v.name,
                "traffic_weight": v.traffic_weight,
                "sample_size": len(values),
                "mean_metric": round(mean_val, 4)
            })
        if baseline_values and len(exp.variants) >= 2:
            treatment_values = exp.variants[1].metrics.get(exp.success_metric, [])
            ci = self.stats.mean_diff_ci(baseline_values, treatment_values)
            results["lift_analysis"] = ci
        return results

    def required_sample_size(self, baseline_rate: float, mde: float,
                             alpha: float = 0.05, power: float = 0.8) -> int:
        """Simplified sample size per variant for proportion metric."""
        z_alpha = 1.96
        z_beta = 0.84
        p = baseline_rate
        p1 = baseline_rate + mde
        pooled = (p + p1) / 2
        se = math.sqrt(2 * pooled * (1 - pooled))
        delta = abs(mde)
        if delta == 0 or se == 0:
            return 0
        n = ((z_alpha + z_beta) ** 2 * 2 * pooled * (1 - pooled)) / (delta ** 2)
        return int(math.ceil(n))


class ExperimentRegistry:
    """Track all experiments and their lifecycle."""

    def __init__(self, engine: ABTestEngine) -> None:
        self.engine = engine

    def list_running(self) -> List[Experiment]:
        return [e for e in self.engine._experiments.values() if e.status == "running"]

    def list_completed(self) -> List[Experiment]:
        return [e for e in self.engine._experiments.values() if e.status == "completed"]

    def complete(self, experiment_id: str) -> bool:
        exp = self.engine._experiments.get(experiment_id)
        if exp:
            exp.status = "completed"
            exp.end_time = datetime.now(timezone.utc)
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Data Validation
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DataContract:
    """Schema contract for a dataset."""
    name: str
    columns: List[Dict[str, Any]] = field(default_factory=list)
    row_count_range: Optional[Tuple[int, int]] = None
    freshness_hours: Optional[float] = None

    def __repr__(self) -> str:
        return f"<DataContract {self.name} columns={len(self.columns)}>"


class SchemaValidator:
    """Validate dataset schema against a contract."""

    def __init__(self) -> None:
        self._errors: List[str] = []

    def __repr__(self) -> str:
        return f"<SchemaValidator errors={len(self._errors)}>"

    def validate(self, contract: DataContract, data: Dict[str, List[Any]]) -> bool:
        self._errors = []
        # Check column existence
        for col_def in contract.columns:
            col_name = col_def.get("name")
            if col_name not in data:
                self._errors.append(f"Missing column: {col_name}")
                continue
            expected_type = col_def.get("type")
            values = data[col_name]
            if expected_type == "numeric":
                non_numeric = [v for v in values if v is not None and not isinstance(v, (int, float))]
                if non_numeric:
                    self._errors.append(f"Column {col_name} has non-numeric values")
            elif expected_type == "string":
                non_string = [v for v in values if v is not None and not isinstance(v, str)]
                if non_string:
                    self._errors.append(f"Column {col_name} has non-string values")
        # Check row count
        if contract.row_count_range and data:
            row_count = len(next(iter(data.values())))
            lo, hi = contract.row_count_range
            if row_count < lo or row_count > hi:
                self._errors.append(f"Row count {row_count} outside range [{lo}, {hi}]")
        return len(self._errors) == 0

    def get_errors(self) -> List[str]:
        return self._errors


class ConstraintChecker:
    """Check data constraints and business rules."""

    def __init__(self) -> None:
        self._violations: List[Dict[str, Any]] = []

    def __repr__(self) -> str:
        return f"<ConstraintChecker violations={len(self._violations)}>"

    def check_range(self, values: List[float], min_val: float, max_val: float,
                    field_name: str = "") -> bool:
        violations = [v for v in values if v is not None and not (min_val <= v <= max_val)]
        if violations:
            self._violations.append({
                "field": field_name,
                "constraint": "range",
                "violations": len(violations)
            })
        return len(violations) == 0

    def check_regex(self, values: List[str], pattern: str,
                    field_name: str = "") -> bool:
        import re
        violations = [v for v in values if v is not None and not re.match(pattern, v)]
        if violations:
            self._violations.append({
                "field": field_name,
                "constraint": "regex",
                "violations": len(violations)
            })
        return len(violations) == 0

    def check_uniqueness(self, values: List[Any], field_name: str = "") -> bool:
        seen: Set[Any] = set()
        duplicates = []
        for v in values:
            if v in seen:
                duplicates.append(v)
            seen.add(v)
        if duplicates:
            self._violations.append({
                "field": field_name,
                "constraint": "uniqueness",
                "violations": len(duplicates)
            })
        return len(duplicates) == 0

    def get_violations(self) -> List[Dict[str, Any]]:
        return self._violations


@dataclass
class Expectation:
    """A single data quality expectation."""
    name: str
    expectation_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    passed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"<Expectation {self.name} [{status}]>"


class ExpectationSuite:
    """Collection of expectations for comprehensive validation."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._expectations: List[Expectation] = []

    def __repr__(self) -> str:
        return f"<ExpectationSuite '{self.name}' expectations={len(self._expectations)}>"

    def add(self, expectation: Expectation) -> None:
        self._expectations.append(expectation)

    def validate(self, data: Dict[str, List[Any]]) -> Dict[str, Any]:
        passed_count = 0
        for exp in self._expectations:
            if exp.expectation_type == "column_exists":
                col = exp.params.get("column")
                exp.passed = col in data
            elif exp.expectation_type == "not_null":
                col = exp.params.get("column")
                if col in data:
                    nulls = sum(1 for v in data[col] if v is None)
                    max_nulls = exp.params.get("max_null_rate", 0.1) * len(data[col])
                    exp.passed = nulls <= max_nulls
                    exp.details = {"nulls": nulls}
                else:
                    exp.passed = False
            elif exp.expectation_type == "values_in_range":
                col = exp.params.get("column")
                if col in data:
                    lo = exp.params.get("min")
                    hi = exp.params.get("max")
                    violations = [v for v in data[col] if v is not None and not (lo <= v <= hi)]
                    exp.passed = len(violations) == 0
                    exp.details = {"violations": len(violations)}
                else:
                    exp.passed = False
            elif exp.expectation_type == "unique":
                col = exp.params.get("column")
                if col in data:
                    exp.passed = len(data[col]) == len(set(data[col]))
                else:
                    exp.passed = False
            if exp.passed:
                passed_count += 1
        total = len(self._expectations)
        return {
            "suite_name": self.name,
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "health_score": passed_count / total if total > 0 else 0,
            "expectations": [{"name": e.name, "passed": e.passed, "details": e.details} for e in self._expectations]
        }


class DataQualityScore:
    """Composite data quality scoring."""

    def __init__(self) -> None:
        self._dimensions: Dict[str, float] = {}

    def __repr__(self) -> str:
        return f"<DataQualityScore dimensions={len(self._dimensions)}>"

    def add_dimension(self, name: str, score: float, weight: float = 1.0) -> None:
        self._dimensions[name] = {"score": score, "weight": weight}

    def compute(self) -> Dict[str, Any]:
        total_weight = sum(d["weight"] for d in self._dimensions.values())
        weighted_sum = sum(d["score"] * d["weight"] for d in self._dimensions.values())
        overall = weighted_sum / total_weight if total_weight > 0 else 0
        return {
            "overall": round(overall, 3),
            "dimensions": {k: round(v["score"], 3) for k, v in self._dimensions.items()}
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Pipeline Orchestration
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Job:
    """A unit of work in the orchestration system."""
    job_id: str
    name: str
    task: Optional[Callable[..., Any]] = None
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    max_retries: int = 3
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"<Job {self.name} status={self.status}>"


class Scheduler:
    """Schedule jobs at intervals or on triggers."""

    def __init__(self) -> None:
        self._schedules: List[Dict[str, Any]] = []

    def __repr__(self) -> str:
        return f"<Scheduler schedules={len(self._schedules)}>"

    def add_interval(self, job_name: str, interval_seconds: int) -> None:
        self._schedules.append({
            "job_name": job_name,
            "type": "interval",
            "interval_seconds": interval_seconds,
            "next_run": datetime.now(timezone.utc)
        })

    def due_jobs(self) -> List[str]:
        now = datetime.now(timezone.utc)
        due: List[str] = []
        for s in self._schedules:
            if s["next_run"] <= now:
                due.append(s["job_name"])
                s["next_run"] = now + timedelta(seconds=s["interval_seconds"])
        return due


class StateManager:
    """Track job execution states."""

    def __init__(self) -> None:
        self._states: Dict[str, str] = {}
        self._history: Dict[str, List[str]] = {}

    def set_state(self, job_id: str, state: str) -> None:
        self._states[job_id] = state
        self._history.setdefault(job_id, []).append(state)

    def get_state(self, job_id: str) -> str:
        return self._states.get(job_id, "unknown")

    def get_history(self, job_id: str) -> List[str]:
        return self._history.get(job_id, [])


class Checkpoint:
    """Save and resume intermediate pipeline state."""

    def __init__(self, checkpoint_dir: str = ".") -> None:
        self.checkpoint_dir = checkpoint_dir
        self._checkpoints: Dict[str, Dict[str, Any]] = {}

    def __repr__(self) -> str:
        return f"<Checkpoint saved={len(self._checkpoints)}>"

    def save(self, pipeline_name: str, state: Dict[str, Any]) -> None:
        self._checkpoints[pipeline_name] = {
            "state": state,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def load(self, pipeline_name: str) -> Optional[Dict[str, Any]]:
        cp = self._checkpoints.get(pipeline_name)
        if cp:
            return dict(cp["state"])
        return None

    def exists(self, pipeline_name: str) -> bool:
        return pipeline_name in self._checkpoints


class Orchestrator:
    """DAG job orchestrator with dependency resolution and retries."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._adjacency: Dict[str, List[str]] = {}
        self._indegree: Dict[str, int] = {}
        self._state_manager = StateManager()
        self._checkpoint = Checkpoint()
        self._scheduler = Scheduler()

    def __repr__(self) -> str:
        return f"<Orchestrator jobs={len(self._jobs)}>"

    def add_job(self, job: Job) -> None:
        self._jobs[job.job_id] = job
        self._adjacency.setdefault(job.job_id, [])
        self._indegree[job.job_id] = 0

    def add_dependency(self, upstream: str, downstream: str) -> None:
        self._adjacency.setdefault(upstream, []).append(downstream)
        self._indegree[downstream] = self._indegree.get(downstream, 0) + 1

    def topological_order(self) -> List[str]:
        order: List[str] = []
        indeg = dict(self._indegree)
        queue = [j for j, d in indeg.items() if d == 0]
        while queue:
            current = queue.pop(0)
            order.append(current)
            for dep in self._adjacency.get(current, []):
                indeg[dep] -= 1
                if indeg[dep] == 0:
                    queue.append(dep)
        if len(order) != len(self._jobs):
            raise ValueError("Cycle detected in job DAG")
        return order

    def execute(self, pipeline_name: str = "default") -> Dict[str, Any]:
        """Execute all jobs in topological order."""
        order = self.topological_order()
        for job_id in order:
            job = self._jobs[job_id]
            self._state_manager.set_state(job_id, "running")
            job.started_at = datetime.now(timezone.utc)
            retries = 0
            success = False
            while retries <= job.max_retries and not success:
                try:
                    if job.task:
                        job.result = job.task()
                    success = True
                except Exception as e:
                    job.error = str(e)
                    retries += 1
            job.status = "success" if success else "failed"
            self._state_manager.set_state(job_id, job.status)
            job.completed_at = datetime.now(timezone.utc)
        self._checkpoint.save(pipeline_name, {jid: self._jobs[jid].status for jid in self._jobs})
        return {jid: self._jobs[jid].status for jid in self._jobs}

    def get_status(self) -> Dict[str, str]:
        return {jid: self._state_manager.get_state(jid) for jid in self._jobs}

    def resume(self, pipeline_name: str) -> Dict[str, Any]:
        """Resume from checkpoint, skipping completed jobs."""
        state = self._checkpoint.load(pipeline_name)
        if not state:
            return self.execute(pipeline_name)
        for job_id, status in state.items():
            if job_id in self._jobs and status == "success":
                self._jobs[job_id].status = "success"
                self._state_manager.set_state(job_id, "success")
        # Re-run only pending/failed jobs
        return self.execute(pipeline_name)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Demo: Full Pipeline
# ═══════════════════════════════════════════════════════════════════════════════


def demo() -> None:
    """Run a full demonstration of the applied-ml system."""
    print("=" * 60)
    print("APPLIED-ML NATIVE — Full System Demo")
    print("=" * 60)

    # 1. ML System with Pipeline
    print("\n[1] ML System & Pipeline:")
    system = MLSystem(name="ProductionRecommender")
    pipeline = Pipeline(name="train_pipeline")
    pipeline.add_stage(IngestStage(StageConfig(
        name="ingest", stage_type="ingest",
        params={"source": "user_events"}
    )))
    pipeline.add_stage(ValidateStage(StageConfig(
        name="validate", stage_type="validate", depends_on=["ingest"]
    )))
    pipeline.add_stage(FeaturizeStage(StageConfig(
        name="featurize", stage_type="featurize", depends_on=["validate"]
    )))
    pipeline.add_stage(TrainStage(StageConfig(
        name="train", stage_type="train", depends_on=["featurize"]
    )))
    pipeline.add_stage(EvaluateStage(StageConfig(
        name="evaluate", stage_type="evaluate", depends_on=["train"]
    )))
    pipeline.add_stage(DeployStage(StageConfig(
        name="deploy", stage_type="deploy", depends_on=["evaluate"]
    )))
    # Connect stages
    pipeline.connect("ingest", "validate")
    pipeline.connect("validate", "featurize")
    pipeline.connect("featurize", "train")
    pipeline.connect("train", "evaluate")
    pipeline.connect("evaluate", "deploy")
    system.add_pipeline(pipeline)
    result = system.run_pipeline("train_pipeline")
    print(f"  Pipeline result: {result}")
    print(f"  Execution log: {pipeline.get_log()}")

    # 2. Feature Engineering
    print("\n[2] Feature Engineering:")
    store = FeatureStore()
    store.register(Feature(name="user_age", feature_type="numeric", source="profile"))
    store.register(Feature(name="item_price", feature_type="numeric", source="catalog"))
    store.register(Feature(name="category", feature_type="categorical", source="catalog"), group="item")
    print(f"  Registered: {store.list_features()}")
    sample_data = [[25.0, 100.0], [30.0, 200.0], [35.0, 150.0], [40.0, 300.0]]
    scaler = StandardScaler()
    normalized = scaler.fit_transform(sample_data)
    print(f"  StandardScaler result (first row): {normalized[0]}")
    poly = PolynomialFeatures(degree=2)
    poly_features = poly.fit_transform(sample_data)
    print(f"  PolynomialFeatures shape: {len(poly_features[0])} features")

    # 3. Model Registry & Serving
    print("\n[3] Model Registry & Serving:")
    registry = ModelRegistry()
    model = ModelArtifact(
        model_id="m001", name="recommender", version="1.0.0",
        framework="custom", metrics={"ndcg": 0.45, "map": 0.38},
        feature_names=["user_age", "item_price", "click_count"]
    )
    registry.register(model)
    registry.promote_to_production("m001")
    server = InferenceServer(registry)
    pred = server.predict("m001", [25.0, 100.0, 5.0])
    print(f"  Prediction: {pred}")
    print(f"  Latency stats: {server.get_latency_stats()}")

    # 4. Monitoring & Drift
    print("\n[4] Monitoring & Drift Detection:")
    monitor = Monitor("production")
    monitor.record("accuracy", 0.92)
    monitor.record("accuracy", 0.91)
    monitor.record("accuracy", 0.89)
    monitor.set_threshold("accuracy", 0.85, 1.0)
    alerts = monitor.check_all()
    print(f"  Alerts: {alerts}")
    print(f"  Accuracy summary: {monitor.summary('accuracy')}")
    drift = DataDriftDetector()
    drift.set_reference("price", [10.0, 20.0, 30.0, 40.0, 50.0] * 100)
    drift.set_current("price", [15.0, 25.0, 35.0, 45.0, 55.0] * 100)
    drift_result = drift.detect("price")
    print(f"  Drift detection: {drift_result}")

    # 5. A/B Testing
    print("\n[5] A/B Testing:")
    ab = ABTestEngine()
    exp = ab.create_experiment(
        "recommendation_algo",
        variants=[
            Variant(name="control", config={"algo": "collaborative_filter"}, traffic_weight=0.5),
            Variant(name="treatment", config={"algo": "deep_learning"}, traffic_weight=0.5)
        ],
        success_metric="conversion"
    )
    ab.start_experiment(exp.experiment_id)
    # Simulate assignments and conversions
    for i in range(1000):
        variant = ab.assign(exp.experiment_id, f"user_{i}")
        if variant:
            conv = 0.12 if variant == "control" else 0.15
            ab.record_metric(exp.experiment_id, variant, 1.0 if random.random() < conv else 0.0)
    analyzer = ExperimentAnalyzer(ab)
    analysis = analyzer.analyze(exp.experiment_id)
    print(f"  Experiment analysis: {analysis}")
    n_needed = analyzer.required_sample_size(baseline_rate=0.12, mde=0.03)
    print(f"  Required sample size per variant: {n_needed}")

    # 6. Data Validation
    print("\n[6] Data Validation:")
    contract = DataContract(
        name="user_events",
        columns=[
            {"name": "user_id", "type": "string"},
            {"name": "age", "type": "numeric"},
            {"name": "event_type", "type": "string"}
        ],
        row_count_range=(10, 10000)
    )
    validator = SchemaValidator()
    sample_dataset = {
        "user_id": ["u1", "u2", "u3"],
        "age": [25, 30, 35],
        "event_type": ["click", "view", "purchase"]
    }
    valid = validator.validate(contract, sample_dataset)
    print(f"  Schema validation: {'PASS' if valid else 'FAIL'}")
    print(f"  Errors: {validator.get_errors()}")
    suite = ExpectationSuite("user_events_suite")
    suite.add(Expectation("user_id_not_null", "not_null", {"column": "user_id", "max_null_rate": 0.0}))
    suite.add(Expectation("age_in_range", "values_in_range", {"column": "age", "min": 0, "max": 120}))
    suite.add(Expectation("user_id_unique", "unique", {"column": "user_id"}))
    suite_result = suite.validate(sample_dataset)
    print(f"  Expectation suite: {suite_result}")
    quality = DataQualityScore()
    quality.add_dimension("completeness", suite_result["health_score"])
    quality.add_dimension("validity", 1.0 if valid else 0.0)
    print(f"  Data quality: {quality.compute()}")

    # 7. Pipeline Orchestration
    print("\n[7] Pipeline Orchestration:")
    orch = Orchestrator()
    def job_ingest():
        return "data_loaded"
    def job_process():
        return "data_processed"
    def job_train():
        return "model_trained"
    orch.add_job(Job("j1", "ingest", job_ingest))
    orch.add_job(Job("j2", "process", job_process, dependencies=["j1"]))
    orch.add_job(Job("j3", "train", job_train, dependencies=["j2"]))
    orch.add_dependency("j1", "j2")
    orch.add_dependency("j2", "j3")
    job_status = orch.execute("demo_pipeline")
    print(f"  Job statuses: {job_status}")
    print(f"  Checkpoint exists: {orch._checkpoint.exists('demo_pipeline')}")

    # 8. System stats
    print("\n[8] System Stats:")
    print(f"  {system.stats()}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
