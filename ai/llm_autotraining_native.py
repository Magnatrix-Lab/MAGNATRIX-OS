"""Auto-Training Pipeline — Data collection, preprocessing, training loop, deployment.

Modul ini menyediakan:
- DataCollector untuk mengumpulkan interaksi LLM dari berbagai sumber
- PreprocessingPipeline untuk cleaning, tokenization, deduplication
- TrainingLoop dengan checkpointing dan early stopping
- DeploymentManager untuk model versioning dan rollout
- Feedback-driven retraining triggers
"""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class DataSource(Enum):
    CHAT = auto()
    FEEDBACK = auto()
    BENCHMARK = auto()
    EXTERNAL = auto()
    SYNTHETIC = auto()


class TrainingStatus(Enum):
    IDLE = auto()
    COLLECTING = auto()
    PREPROCESSING = auto()
    TRAINING = auto()
    VALIDATING = auto()
    DEPLOYING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class TrainingSample:
    """Single training example."""
    sample_id: str
    prompt: str
    response: str
    source: DataSource
    quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.sha256(f"{self.prompt}:{self.response}".encode()).hexdigest()[:16]


@dataclass
class DatasetSplit:
    """Train/validation/test split."""
    train: List[TrainingSample]
    val: List[TrainingSample]
    test: List[TrainingSample]
    train_size: int = 0
    val_size: int = 0
    test_size: int = 0

    def __post_init__(self):
        self.train_size = len(self.train)
        self.val_size = len(self.val)
        self.test_size = len(self.test)


@dataclass
class Checkpoint:
    """Training checkpoint."""
    checkpoint_id: str
    epoch: int
    step: int
    metrics: Dict[str, float]
    path: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class ModelVersion:
    """Deployed model version."""
    version_id: str
    name: str
    checkpoint_id: str
    metrics: Dict[str, float]
    status: str = "staging"  # staging, production, archived, rolled_back
    deployed_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataCollector:
    """Collect and manage training data from multiple sources."""

    def __init__(self, min_quality: float = 0.5):
        self.min_quality = min_quality
        self._samples: List[TrainingSample] = []
        self._hashes: Set[str] = set()
        self._source_stats: Dict[DataSource, int] = {s: 0 for s in DataSource}

    def collect(self, prompt: str, response: str, source: DataSource = DataSource.CHAT,
                quality: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> Optional[TrainingSample]:
        if quality < self.min_quality:
            return None
        sample = TrainingSample(
            sample_id=str(uuid.uuid4())[:12],
            prompt=prompt[:2000],
            response=response[:4000],
            source=source,
            quality_score=quality,
            metadata=metadata or {}
        )
        if sample.hash in self._hashes:
            return None  # Deduplicate
        self._hashes.add(sample.hash)
        self._samples.append(sample)
        self._source_stats[source] += 1
        return sample

    def collect_batch(self, items: List[Tuple[str, str, DataSource, float]]) -> List[TrainingSample]:
        collected = []
        for prompt, response, source, quality in items:
            s = self.collect(prompt, response, source, quality)
            if s:
                collected.append(s)
        return collected

    def filter_by_quality(self, threshold: float) -> List[TrainingSample]:
        return [s for s in self._samples if s.quality_score >= threshold]

    def filter_by_source(self, source: DataSource) -> List[TrainingSample]:
        return [s for s in self._samples if s.source == source]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_samples": len(self._samples),
            "unique_hashes": len(self._hashes),
            "source_breakdown": {k.name: v for k, v in self._source_stats.items()},
            "avg_quality": sum(s.quality_score for s in self._samples) / max(len(self._samples), 1),
        }

    def split(self, train_ratio: float = 0.8, val_ratio: float = 0.1) -> DatasetSplit:
        import random
        shuffled = list(self._samples)
        random.seed(42)
        random.shuffle(shuffled)
        n = len(shuffled)
        t = int(n * train_ratio)
        v = int(n * val_ratio)
        return DatasetSplit(
            train=shuffled[:t],
            val=shuffled[t:t+v],
            test=shuffled[t+v:]
        )


class PreprocessingPipeline:
    """Clean, normalize, and prepare data for training."""

    def __init__(self):
        self._steps: List[Tuple[str, Callable[[TrainingSample], TrainingSample]]] = []
        self._stats: Dict[str, int] = {"processed": 0, "dropped": 0, "modified": 0}

    def add_step(self, name: str, fn: Callable[[TrainingSample], TrainingSample]) -> PreprocessingPipeline:
        self._steps.append((name, fn))
        return self

    def run(self, samples: List[TrainingSample]) -> List[TrainingSample]:
        results = []
        for sample in samples:
            current = sample
            for name, fn in self._steps:
                try:
                    current = fn(current)
                except Exception as e:
                    self._stats["dropped"] += 1
                    break
            else:
                if current.hash != sample.hash:
                    self._stats["modified"] += 1
                results.append(current)
                self._stats["processed"] += 1
        return results

    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)

    @staticmethod
    def default() -> PreprocessingPipeline:
        """Factory for default cleaning pipeline."""
        pp = PreprocessingPipeline()
        # Trim whitespace
        pp.add_step("trim", lambda s: TrainingSample(
            s.sample_id, s.prompt.strip(), s.response.strip(), s.source,
            s.quality_score, s.metadata, s.created_at
        ))
        # Filter empty responses
        pp.add_step("non_empty", lambda s: s if s.response else (_ for _ in ()).throw(ValueError("Empty response")))
        # Length filter
        pp.add_step("length", lambda s: s if len(s.response) > 10 else (_ for _ in ()).throw(ValueError("Too short")))
        return pp


class TrainingLoop:
    """Simulated training loop with checkpointing and metrics."""

    def __init__(self, max_epochs: int = 10, patience: int = 3, checkpoint_dir: str = "./checkpoints"):
        self.max_epochs = max_epochs
        self.patience = patience
        self.checkpoint_dir = checkpoint_dir
        self._checkpoints: List[Checkpoint] = []
        self._status = TrainingStatus.IDLE
        self._metrics_history: List[Dict[str, float]] = []
        self._best_metric: float = -1.0
        self._patience_counter: int = 0

    def train(self, dataset: DatasetSplit, train_fn: Optional[Callable[[List[TrainingSample], int], Dict[str, float]]] = None) -> List[Checkpoint]:
        self._status = TrainingStatus.TRAINING
        train_fn = train_fn or self._default_train_fn
        for epoch in range(1, self.max_epochs + 1):
            metrics = train_fn(dataset.train, epoch)
            val_metrics = self._validate(dataset.val)
            metrics.update({f"val_{k}": v for k, v in val_metrics.items()})
            self._metrics_history.append(metrics)

            ckpt = Checkpoint(
                checkpoint_id=str(uuid.uuid4())[:12],
                epoch=epoch,
                step=epoch * len(dataset.train),
                metrics=metrics,
                path=f"{self.checkpoint_dir}/ckpt_{epoch}.json"
            )
            self._checkpoints.append(ckpt)

            # Early stopping check
            val_loss = metrics.get("val_loss", 999.0)
            if val_loss < self._best_metric or self._best_metric < 0:
                self._best_metric = val_loss
                self._patience_counter = 0
            else:
                self._patience_counter += 1
                if self._patience_counter >= self.patience:
                    self._status = TrainingStatus.COMPLETED
                    break
        else:
            self._status = TrainingStatus.COMPLETED
        return self._checkpoints

    def _default_train_fn(self, train_data: List[TrainingSample], epoch: int) -> Dict[str, float]:
        # Simulated training: loss improves over epochs
        loss = max(0.5, 2.0 - epoch * 0.15 + (uuid.uuid4().int % 100) / 1000)
        acc = min(0.95, 0.6 + epoch * 0.03)
        return {"loss": round(loss, 4), "accuracy": round(acc, 4)}

    def _validate(self, val_data: List[TrainingSample]) -> Dict[str, float]:
        loss = max(0.4, 1.5 - len(self._checkpoints) * 0.1)
        acc = min(0.95, 0.65 + len(self._checkpoints) * 0.02)
        return {"loss": round(loss, 4), "accuracy": round(acc, 4)}

    def get_best_checkpoint(self) -> Optional[Checkpoint]:
        if not self._checkpoints:
            return None
        return min(self._checkpoints, key=lambda c: c.metrics.get("val_loss", 999.0))

    def status(self) -> TrainingStatus:
        return self._status


class DeploymentManager:
    """Manage model versions, staging, and rollout."""

    def __init__(self):
        self._versions: Dict[str, ModelVersion] = {}
        self._production: Optional[str] = None

    def stage(self, checkpoint: Checkpoint, name: str, metadata: Optional[Dict[str, Any]] = None) -> ModelVersion:
        vid = str(uuid.uuid4())[:12]
        ver = ModelVersion(
            version_id=vid,
            name=name,
            checkpoint_id=checkpoint.checkpoint_id,
            metrics=checkpoint.metrics,
            status="staging",
            metadata=metadata or {}
        )
        self._versions[vid] = ver
        return ver

    def promote(self, version_id: str) -> Optional[ModelVersion]:
        ver = self._versions.get(version_id)
        if not ver:
            return None
        # Demote current production
        if self._production and self._production in self._versions:
            self._versions[self._production].status = "archived"
        ver.status = "production"
        self._production = version_id
        return ver

    def rollback(self) -> Optional[ModelVersion]:
        # Find previous production (simplified: any non-production archived version)
        for vid, ver in sorted(self._versions.items(), key=lambda x: x[1].deployed_at, reverse=True):
            if vid != self._production and ver.status == "archived":
                return self.promote(vid)
        return None

    def get_production(self) -> Optional[ModelVersion]:
        if self._production:
            return self._versions.get(self._production)
        return None

    def list_versions(self) -> List[ModelVersion]:
        return sorted(self._versions.values(), key=lambda v: v.deployed_at, reverse=True)


class AutoTrainingOrchestrator:
    """End-to-end orchestrator: collect → preprocess → train → deploy."""

    def __init__(self, min_samples: int = 100):
        self.min_samples = min_samples
        self.collector = DataCollector()
        self.preprocessor = PreprocessingPipeline.default()
        self.trainer = TrainingLoop()
        self.deployer = DeploymentManager()
        self._runs: List[Dict[str, Any]] = []
        self._trigger_conditions: List[Callable[[AutoTrainingOrchestrator], bool]] = []

    def add_trigger(self, condition: Callable[[AutoTrainingOrchestrator], bool]) -> None:
        self._trigger_conditions.append(condition)

    def should_retrain(self) -> bool:
        return any(c(self) for c in self._trigger_conditions) or self.collector.get_stats()["total_samples"] >= self.min_samples

    def run(self) -> Dict[str, Any]:
        if not self.should_retrain():
            return {"status": "skipped", "reason": "Trigger conditions not met"}

        # 1. Split
        dataset = self.collector.split()
        if dataset.train_size < 10:
            return {"status": "failed", "reason": "Insufficient data"}

        # 2. Preprocess
        self.trainer._status = TrainingStatus.PREPROCESSING
        dataset.train = self.preprocessor.run(dataset.train)
        dataset.val = self.preprocessor.run(dataset.val)
        dataset.test = self.preprocessor.run(dataset.test)

        # 3. Train
        checkpoints = self.trainer.train(dataset)
        best = self.trainer.get_best_checkpoint()

        # 4. Deploy
        if best:
            self.trainer._status = TrainingStatus.DEPLOYING
            ver = self.deployer.stage(best, f"model-v{len(self._runs)+1}")
            self.deployer.promote(ver.version_id)

        run_record = {
            "run_id": str(uuid.uuid4())[:12],
            "timestamp": time.time(),
            "dataset": {"train": dataset.train_size, "val": dataset.val_size, "test": dataset.test_size},
            "checkpoints": len(checkpoints),
            "best_checkpoint": best.checkpoint_id if best else None,
            "production_version": self.deployer.get_production().version_id if self.deployer.get_production() else None,
        }
        self._runs.append(run_record)
        self.trainer._status = TrainingStatus.COMPLETED
        return run_record

    def get_status(self) -> Dict[str, Any]:
        return {
            "training_status": self.trainer.status().name,
            "data_stats": self.collector.get_stats(),
            "preprocess_stats": self.preprocessor.get_stats(),
            "versions": len(self.deployer._versions),
            "production": self.deployer._production,
            "runs": len(self._runs),
        }

    def export_report(self, path: str) -> None:
        report = {
            "status": self.get_status(),
            "runs": self._runs,
            "versions": [{
                "version_id": v.version_id,
                "name": v.name,
                "status": v.status,
                "metrics": v.metrics,
                "deployed_at": v.deployed_at
            } for v in self.deployer.list_versions()]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("AUTO-TRAINING PIPELINE DEMO")
    print("=" * 70)

    # 1. Data collection
    print("\n[1] Data Collection")
    collector = DataCollector(min_quality=0.6)
    samples = [
        ("What is Python?", "Python is a programming language.", DataSource.CHAT, 0.9),
        ("Explain recursion", "Recursion is when a function calls itself.", DataSource.CHAT, 0.85),
        ("2+2", "4", DataSource.BENCHMARK, 1.0),
        ("Bad input", "", DataSource.CHAT, 0.2),  # Dropped by quality
        ("Explain loops", "Loops repeat code. Loops repeat code.", DataSource.SYNTHETIC, 0.7),
        ("What is AI?", "AI stands for artificial intelligence.", DataSource.EXTERNAL, 0.88),
    ]
    collected = collector.collect_batch(samples)
    print(f"  Collected: {len(collected)} samples")
    print(f"  Stats: {collector.get_stats()}")

    # 2. Preprocessing
    print("\n[2] Preprocessing")
    pp = PreprocessingPipeline.default()
    dataset = collector.split(train_ratio=0.7, val_ratio=0.15)
    clean_train = pp.run(dataset.train)
    print(f"  Train: {dataset.train_size} -> {len(clean_train)} after preprocessing")
    print(f"  Preprocess stats: {pp.get_stats()}")

    # 3. Training loop
    print("\n[3] Training Loop")
    loop = TrainingLoop(max_epochs=5, patience=2)
    checkpoints = loop.train(dataset)
    print(f"  Checkpoints: {len(checkpoints)}")
    for ckpt in checkpoints:
        print(f"    Epoch {ckpt.epoch}: loss={ckpt.metrics['loss']}, val_loss={ckpt.metrics['val_loss']}, acc={ckpt.metrics['accuracy']}")
    best = loop.get_best_checkpoint()
    print(f"  Best checkpoint: {best.checkpoint_id} (epoch {best.epoch})")

    # 4. Deployment
    print("\n[4] Deployment")
    dm = DeploymentManager()
    v1 = dm.stage(best, "llm-v1", {"author": "magnatrix"})
    print(f"  Staged: {v1.version_id} -> {v1.status}")
    dm.promote(v1.version_id)
    print(f"  Promoted to production: {dm.get_production().version_id}")
    v2 = dm.stage(checkpoints[-1], "llm-v2")
    dm.promote(v2.version_id)
    print(f"  New production: {dm.get_production().version_id}")
    print(f"  Versions: {len(dm.list_versions())}")

    # 5. Full orchestrator
    print("\n[5] Full Orchestrator")
    orch = AutoTrainingOrchestrator(min_samples=3)
    # Add synthetic data
    for i in range(20):
        orch.collector.collect(f"Q{i}", f"A{i}", DataSource.SYNTHETIC, 0.8)
    # Trigger on data count
    orch.add_trigger(lambda o: o.collector.get_stats()["total_samples"] >= 5)
    result = orch.run()
    print(f"  Run result: {result}")
    print(f"  Status: {orch.get_status()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
