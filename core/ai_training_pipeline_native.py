#!/usr/bin/env python3
"""
AI Training Pipeline for MAGNATRIX-OS
Fine-tune local LLM with custom data, dataset manager, training loop,
model versioning, evaluation metrics. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import os
import random
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class DatasetEntry:
    """Single training data entry."""
    instruction: str
    input: str = ""
    output: str = ""
    context: str = ""
    source: str = ""
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingConfig:
    """Configuration for training run."""
    model_name: str = "llama3"
    epochs: int = 3
    learning_rate: float = 0.0001
    batch_size: int = 4
    max_seq_length: int = 2048
    warmup_steps: int = 100
    save_interval: int = 500
    eval_interval: int = 100
    checkpoint_dir: str = "./checkpoints"


@dataclass
class TrainingMetrics:
    """Metrics from a training run."""
    epoch: int
    step: int
    loss: float
    perplexity: float
    learning_rate: float
    timestamp: float


class DatasetManager:
    """Manage training datasets."""

    FORMATS = {"alpaca", "sharegpt", "raw", "jsonl"}

    def __init__(self, store_dir: str = "./data/datasets") -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._entries: List[DatasetEntry] = []
        self._lock = threading.Lock()

    def load_file(self, path: str, format: str = "auto") -> int:
        """Load dataset from file."""
        file_path = Path(path)
        if not file_path.exists():
            return 0

        text = file_path.read_text(encoding="utf-8")

        if format == "auto":
            if text.strip().startswith("["):
                format = "json"
            elif "### Instruction:" in text:
                format = "alpaca"
            else:
                format = "raw"

        count = 0
        if format == "json":
            data = json.loads(text)
            for item in data:
                entry = DatasetEntry(
                    instruction=item.get("instruction", ""),
                    input=item.get("input", ""),
                    output=item.get("output", ""),
                    context=item.get("context", ""),
                    source=item.get("source", str(path)),
                )
                self._entries.append(entry)
                count += 1
        elif format == "alpaca":
            # Parse Alpaca format: ### Instruction: ... ### Response: ...
            pattern = r"### Instruction:\s*(.+?)\s*### Input:\s*(.*?)\s*### Response:\s*(.+)"
            for match in re.finditer(pattern, text, re.DOTALL):
                entry = DatasetEntry(
                    instruction=match.group(1).strip(),
                    input=match.group(2).strip(),
                    output=match.group(3).strip(),
                    source=str(path),
                )
                self._entries.append(entry)
                count += 1
        elif format == "jsonl":
            for line in text.strip().splitlines():
                if line.strip():
                    item = json.loads(line)
                    entry = DatasetEntry(
                        instruction=item.get("instruction", ""),
                        input=item.get("input", ""),
                        output=item.get("output", ""),
                        source=str(path),
                    )
                    self._entries.append(entry)
                    count += 1
        elif format == "raw":
            # Split by double newline
            chunks = text.split("\n\n")
            for chunk in chunks:
                if chunk.strip():
                    entry = DatasetEntry(
                        instruction="",
                        input="",
                        output=chunk.strip(),
                        source=str(path),
                    )
                    self._entries.append(entry)
                    count += 1

        return count

    def save_dataset(self, name: str) -> str:
        """Save current dataset to JSON."""
        path = self.store_dir / f"{name}.json"
        data = [
            {
                "instruction": e.instruction,
                "input": e.input,
                "output": e.output,
                "context": e.context,
                "source": e.source,
            }
            for e in self._entries
        ]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_chars = sum(len(e.instruction) + len(e.input) + len(e.output) for e in self._entries)
            sources = {}
            for e in self._entries:
                sources[e.source] = sources.get(e.source, 0) + 1
            return {
                "entries": len(self._entries),
                "total_chars": total_chars,
                "avg_entry_length": total_chars / len(self._entries) if self._entries else 0,
                "sources": sources,
            }

    def split(self, train_ratio: float = 0.8) -> Tuple[List[DatasetEntry], List[DatasetEntry]]:
        """Split dataset into train/test."""
        entries = self._entries[:]
        random.shuffle(entries)
        split_idx = int(len(entries) * train_ratio)
        return entries[:split_idx], entries[split_idx:]


class TrainingEngine:
    """Simulated training engine for fine-tuning."""

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config
        self._metrics: List[TrainingMetrics] = []
        self._running = False
        self._lock = threading.Lock()
        self._checkpoint_dir = Path(config.checkpoint_dir)
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._progress_callback: Optional[Callable[[TrainingMetrics], None]] = None

    def train(self, dataset: List[DatasetEntry]) -> Dict[str, Any]:
        """Run training loop."""
        self._running = True
        total_steps = len(dataset) * self.config.epochs // self.config.batch_size

        print(f"[Training] Starting {self.config.epochs} epochs, {total_steps} steps")

        for epoch in range(self.config.epochs):
            if not self._running:
                break

            for step in range(0, len(dataset), self.config.batch_size):
                if not self._running:
                    break

                batch = dataset[step:step + self.config.batch_size]

                # Simulate forward pass + loss calculation
                loss = self._simulate_loss(epoch, step, batch)
                lr = self._get_lr(epoch, step)

                metric = TrainingMetrics(
                    epoch=epoch + 1,
                    step=step // self.config.batch_size + 1,
                    loss=loss,
                    perplexity=2.718 ** loss,
                    learning_rate=lr,
                    timestamp=time.time(),
                )

                with self._lock:
                    self._metrics.append(metric)

                if self._progress_callback:
                    self._progress_callback(metric)

                # Save checkpoint
                if metric.step % self.config.save_interval == 0:
                    self._save_checkpoint(epoch, metric.step)

                # Simulate step time
                time.sleep(0.001)

            print(f"[Training] Epoch {epoch + 1}/{self.config.epochs} complete")

        self._running = False
        return self._generate_report()

    def _simulate_loss(self, epoch: int, step: int, batch: List[DatasetEntry]) -> float:
        """Simulate training loss with convergence pattern."""
        base = 2.0
        convergence = 0.3
        noise = random.uniform(-0.05, 0.05)
        progress = (epoch * len(batch) + step) / (self.config.epochs * len(batch) + 1)
        return max(convergence, base * (1 - progress) + noise)

    def _get_lr(self, epoch: int, step: int) -> float:
        """Calculate learning rate with warmup and decay."""
        global_step = epoch * 1000 + step
        if global_step < self.config.warmup_steps:
            return self.config.learning_rate * (global_step / self.config.warmup_steps)
        return self.config.learning_rate * 0.95 ** (global_step // 1000)

    def _save_checkpoint(self, epoch: int, step: int) -> str:
        checkpoint = {
            "epoch": epoch,
            "step": step,
            "config": self.config.__dict__,
            "metrics": [m.__dict__ for m in self._metrics[-10:]],
            "timestamp": time.time(),
        }
        path = self._checkpoint_dir / f"checkpoint_e{epoch}_s{step}.json"
        path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")
        return str(path)

    def _generate_report(self) -> Dict[str, Any]:
        with self._lock:
            if not self._metrics:
                return {"error": "No training data"}
            losses = [m.loss for m in self._metrics]
            return {
                "final_loss": losses[-1],
                "initial_loss": losses[0],
                "avg_loss": sum(losses) / len(losses),
                "min_loss": min(losses),
                "epochs": self.config.epochs,
                "total_steps": len(self._metrics),
                "checkpoints": len(list(self._checkpoint_dir.glob("checkpoint_*.json"))),
            }

    def stop(self) -> None:
        self._running = False

    def on_progress(self, callback: Callable[[TrainingMetrics], None]) -> None:
        self._progress_callback = callback

    def get_metrics(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [m.__dict__ for m in self._metrics]


class ModelVersionManager:
    """Manage model versions and checkpoints."""

    def __init__(self, store_dir: str = "./data/models") -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._versions: List[Dict[str, Any]] = []

    def register_version(self, name: str, checkpoint_path: str, metrics: Dict[str, Any]) -> str:
        version = {
            "id": f"v_{int(time.time())}",
            "name": name,
            "checkpoint": checkpoint_path,
            "metrics": metrics,
            "created_at": time.time(),
        }
        self._versions.append(version)
        # Save version registry
        (self.store_dir / "versions.json").write_text(
            json.dumps(self._versions, indent=2), encoding="utf-8"
        )
        return version["id"]

    def list_versions(self) -> List[Dict[str, Any]]:
        return sorted(self._versions, key=lambda v: v["created_at"], reverse=True)

    def get_best_version(self, metric: str = "final_loss") -> Optional[Dict[str, Any]]:
        if not self._versions:
            return None
        return min(self._versions, key=lambda v: v.get("metrics", {}).get(metric, float("inf")))


class AITrainingPipeline:
    """Main pipeline combining dataset, training, and versioning."""

    def __init__(self, repo_root: str = "") -> None:
        self.root = Path(repo_root).resolve() if repo_root else Path.cwd()
        self.dataset = DatasetManager(str(self.root / "data" / "datasets"))
        self.version_manager = ModelVersionManager(str(self.root / "data" / "models"))
        self._engine: Optional[TrainingEngine] = None

    def create_training_config(self, model_name: str = "llama3", epochs: int = 3) -> TrainingConfig:
        return TrainingConfig(
            model_name=model_name,
            epochs=epochs,
            checkpoint_dir=str(self.root / "data" / "checkpoints"),
        )

    def run_training(self, config: TrainingConfig, dataset_name: Optional[str] = None) -> Dict[str, Any]:
        """Run full training pipeline."""
        if dataset_name:
            self.dataset.load_file(str(self.root / "data" / "datasets" / f"{dataset_name}.json"))

        train_data, test_data = self.dataset.split()
        if not train_data:
            return {"error": "No training data available"}

        self._engine = TrainingEngine(config)
        report = self._engine.train(train_data)

        # Save version
        checkpoint = self._engine._save_checkpoint(report.get("epochs", 0), 0)
        version_id = self.version_manager.register_version(
            f"{config.model_name}_v{report['epochs']}", checkpoint, report
        )

        return {
            "report": report,
            "version_id": version_id,
            "dataset_stats": self.dataset.get_stats(),
        }

    def stop_training(self) -> None:
        if self._engine:
            self._engine.stop()

    def stats(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset.get_stats(),
            "versions": len(self.version_manager.list_versions()),
            "training": self._engine is not None and self._engine._running,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== AI Training Pipeline Demo ===\n")
    pipeline = AITrainingPipeline(repo_root="/tmp/magnatrix_training")

    # Create sample dataset
    sample_data = [
        {"instruction": "Explain quantum computing", "output": "Quantum computing uses qubits..."},
        {"instruction": "What is AI", "output": "AI is artificial intelligence..."},
        {"instruction": "How to cook pasta", "output": "Boil water, add pasta..."},
    ]
    dataset_path = Path("/tmp/magnatrix_training/data/datasets/sample.json")
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text(json.dumps(sample_data))

    pipeline.dataset.load_file(str(dataset_path))
    print(f"Dataset stats: {pipeline.dataset.get_stats()}")

    config = pipeline.create_training_config("llama3", epochs=2)
    print(f"\nTraining config: {config}")

    print("\nRunning training (simulated)...")
    result = pipeline.run_training(config)
    print(f"Training report: {result['report']}")
    print(f"Version: {result['version_id']}")

    print(f"\nPipeline stats: {pipeline.stats()}")


if __name__ == "__main__":
    _demo()
