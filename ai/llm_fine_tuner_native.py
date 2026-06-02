"""Fine-Tuner — Parameter-efficient fine-tuning dengan LoRA/QLoRA adapter management.

Modul ini menyediakan:
- AdapterConfig untuk LoRA/QLoRA hyperparameters
- AdapterManager untuk register, load, merge adapters
- FineTuningDataset untuk manage training examples
- FineTuningLoop untuk training loop dengan checkpointing
- FineTunerEngine untuk end-to-end fine-tuning pipeline
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class AdapterType(Enum):
    LORA = "lora"
    QLORA = "qlora"
    PREFIX = "prefix"
    PROMPT = "prompt"


class FineTuneStatus(Enum):
    IDLE = auto()
    PREPARING = auto()
    TRAINING = auto()
    VALIDATING = auto()
    MERGING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class AdapterConfig:
    """LoRA/QLoRA configuration."""
    adapter_id: str
    name: str
    adapter_type: AdapterType
    r: int = 8  # LoRA rank
    lora_alpha: float = 16.0
    lora_dropout: float = 0.05
    target_modules: List[str] = field(default_factory=lambda: ["q_proj", "v_proj"])
    bias: str = "none"
    use_rslora: bool = False  # Rank-stabilized LoRA
    quant_4bit: bool = False  # QLoRA 4-bit quantization
    quant_8bit: bool = False  # 8-bit quantization
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "name": self.name,
            "type": self.adapter_type.value,
            "r": self.r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "target_modules": self.target_modules,
            "quant_4bit": self.quant_4bit,
            "quant_8bit": self.quant_8bit,
        }


@dataclass
class FineTuneExample:
    """Single fine-tuning example."""
    example_id: str
    prompt: str
    completion: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FineTuneCheckpoint:
    """Training checkpoint."""
    checkpoint_id: str
    step: int
    epoch: int
    loss: float
    val_loss: float = 0.0
    adapter_id: str = ""
    path: str = ""
    created_at: float = field(default_factory=time.time)


class AdapterManager:
    """Manage LoRA/QLoRA adapters."""

    def __init__(self):
        self._adapters: Dict[str, AdapterConfig] = {}
        self._active: Optional[str] = None
        self._merged: Dict[str, str] = {}  # adapter_id -> merged_model_path

    def register(self, config: AdapterConfig) -> None:
        self._adapters[config.adapter_id] = config

    def get(self, adapter_id: str) -> Optional[AdapterConfig]:
        return self._adapters.get(adapter_id)

    def activate(self, adapter_id: str) -> bool:
        if adapter_id in self._adapters:
            self._active = adapter_id
            return True
        return False

    def get_active(self) -> Optional[AdapterConfig]:
        if self._active:
            return self._adapters.get(self._active)
        return None

    def merge(self, adapter_id: str, base_model_path: str) -> str:
        """Simulate adapter merging with base model."""
        merged_id = f"merged-{adapter_id}-{str(uuid.uuid4())[:8]}"
        self._merged[adapter_id] = merged_id
        return merged_id

    def list_all(self) -> List[AdapterConfig]:
        return list(self._adapters.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_adapters": len(self._adapters),
            "active": self._active,
            "merged": len(self._merged),
        }


class FineTuningDataset:
    """Manage fine-tuning examples."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._examples: List[FineTuneExample] = []
        self._stats: Dict[str, Any] = {"total_tokens": 0, "avg_length": 0}

    def add(self, prompt: str, completion: str, weight: float = 1.0) -> FineTuneExample:
        ex = FineTuneExample(
            example_id=str(uuid.uuid4())[:12],
            prompt=prompt[:2000],
            completion=completion[:4000],
            weight=weight,
        )
        self._examples.append(ex)
        if len(self._examples) > self.max_size:
            self._examples = self._examples[-self.max_size:]
        self._update_stats()
        return ex

    def add_batch(self, items: List[Tuple[str, str]]) -> List[FineTuneExample]:
        return [self.add(p, c) for p, c in items]

    def split(self, train_ratio: float = 0.8, val_ratio: float = 0.1) -> Tuple[List[FineTuneExample], List[FineTuneExample], List[FineTuneExample]]:
        import random
        shuffled = list(self._examples)
        random.seed(42)
        random.shuffle(shuffled)
        n = len(shuffled)
        t = int(n * train_ratio)
        v = int(n * val_ratio)
        return shuffled[:t], shuffled[t:t+v], shuffled[t+v:]

    def _update_stats(self) -> None:
        total_len = sum(len(e.prompt) + len(e.completion) for e in self._examples)
        self._stats = {
            "total_examples": len(self._examples),
            "total_chars": total_len,
            "avg_example_length": total_len / max(len(self._examples), 1),
        }

    def get_stats(self) -> Dict[str, Any]:
        return self._stats

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{"prompt": e.prompt, "completion": e.completion, "weight": e.weight} for e in self._examples], f, indent=2)


class FineTuningLoop:
    """Training loop dengan checkpointing."""

    def __init__(self, epochs: int = 3, learning_rate: float = 1e-4, batch_size: int = 4,
                 warmup_steps: int = 100, save_every: int = 100):
        self.epochs = epochs
        self.lr = learning_rate
        self.batch_size = batch_size
        self.warmup_steps = warmup_steps
        self.save_every = save_every
        self._checkpoints: List[FineTuneCheckpoint] = []
        self._status = FineTuneStatus.IDLE
        self._current_step = 0

    def train(self, dataset: FineTuningDataset, adapter_id: str,
              train_fn: Optional[Callable[[List[FineTuneExample], int], Tuple[float, float]]] = None) -> List[FineTuneCheckpoint]:
        self._status = FineTuneStatus.TRAINING
        train_fn = train_fn or self._default_train_fn
        train_data, val_data, _ = dataset.split()
        num_batches = max(1, len(train_data) // self.batch_size)

        for epoch in range(self.epochs):
            for batch_idx in range(num_batches):
                self._current_step += 1
                batch = train_data[batch_idx * self.batch_size:(batch_idx + 1) * self.batch_size]
                loss, val_loss = train_fn(batch, self._current_step)

                if self._current_step % self.save_every == 0:
                    ckpt = FineTuneCheckpoint(
                        checkpoint_id=f"ckpt-{self._current_step}",
                        step=self._current_step,
                        epoch=epoch,
                        loss=round(loss, 4),
                        val_loss=round(val_loss, 4),
                        adapter_id=adapter_id,
                    )
                    self._checkpoints.append(ckpt)

        self._status = FineTuneStatus.COMPLETED
        return self._checkpoints

    def _default_train_fn(self, batch: List[FineTuneExample], step: int) -> Tuple[float, float]:
        # Simulated training: loss decreases with steps
        base_loss = 2.0 - (step / 1000) * 0.5
        noise = (uuid.uuid4().int % 100) / 1000
        loss = max(0.1, base_loss + noise)
        val_loss = max(0.15, loss + 0.05)
        return round(loss, 4), round(val_loss, 4)

    def get_status(self) -> FineTuneStatus:
        return self._status

    def get_best_checkpoint(self) -> Optional[FineTuneCheckpoint]:
        if not self._checkpoints:
            return None
        return min(self._checkpoints, key=lambda c: c.val_loss)


class FineTunerEngine:
    """End-to-end fine-tuning pipeline."""

    def __init__(self):
        self.adapters = AdapterManager()
        self.dataset = FineTuningDataset()
        self.trainer = FineTuningLoop()
        self._runs: List[Dict[str, Any]] = []

    def create_adapter(self, name: str, adapter_type: AdapterType = AdapterType.LORA,
                       r: int = 8, target_modules: Optional[List[str]] = None) -> AdapterConfig:
        config = AdapterConfig(
            adapter_id=str(uuid.uuid4())[:12],
            name=name,
            adapter_type=adapter_type,
            r=r,
            target_modules=target_modules or ["q_proj", "v_proj"],
        )
        self.adapters.register(config)
        return config

    def run(self, adapter_id: str, train_fn: Optional[Callable[[List[FineTuneExample], int], Tuple[float, float]]] = None) -> Dict[str, Any]:
        adapter = self.adapters.get(adapter_id)
        if not adapter:
            return {"status": "failed", "reason": "Adapter not found"}
        if self.dataset.get_stats()["total_examples"] < 1:
            return {"status": "failed", "reason": "No training data"}

        checkpoints = self.trainer.train(self.dataset, adapter_id, train_fn)
        best = self.trainer.get_best_checkpoint()
        self.adapters.activate(adapter_id)

        run = {
            "run_id": str(uuid.uuid4())[:12],
            "adapter": adapter.to_dict(),
            "checkpoints": len(checkpoints),
            "best_checkpoint": best.to_dict() if best else None,
            "dataset_stats": self.dataset.get_stats(),
            "status": self.trainer.get_status().name,
        }
        self._runs.append(run)
        return run

    def merge_adapter(self, adapter_id: str, base_model: str) -> str:
        return self.adapters.merge(adapter_id, base_model)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "adapters": self.adapters.get_stats(),
            "dataset": self.dataset.get_stats(),
            "runs": len(self._runs),
            "status": self.trainer.get_status().name,
        }

    def export_report(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "runs": self._runs,
                "stats": self.get_stats(),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("FINE-TUNER DEMO")
    print("=" * 70)

    engine = FineTunerEngine()

    # 1. Create adapter
    print("\n[1] Create Adapter")
    adapter = engine.create_adapter("math-lora", AdapterType.LORA, r=16, target_modules=["q_proj", "v_proj", "k_proj"])
    print(f"  Adapter: {adapter.adapter_id}, type={adapter.adapter_type.value}, r={adapter.r}")
    print(f"  Target modules: {adapter.target_modules}")

    # 2. Create QLoRA adapter
    print("\n[2] Create QLoRA Adapter")
    qlora = engine.create_adapter("code-qlora", AdapterType.QLORA, r=32)
    qlora.quant_4bit = True
    print(f"  QLoRA: {qlora.adapter_id}, r={qlora.r}, 4bit={qlora.quant_4bit}")

    # 3. Add training data
    print("\n[3] Training Data")
    examples = [
        ("What is 2+2?", "4"),
        ("Solve x+5=10", "x=5"),
        ("What is the derivative of x^2?", "2x"),
        ("Calculate integral of 2x", "x^2 + C"),
        ("What is 3*7?", "21"),
    ]
    engine.dataset.add_batch(examples)
    print(f"  Dataset: {engine.dataset.get_stats()}")

    # 4. Training
    print("\n[4] Training")
    result = engine.run(adapter.adapter_id)
    print(f"  Run: {result['run_id']}")
    print(f"  Checkpoints: {result['checkpoints']}")
    print(f"  Best: {result['best_checkpoint']}")
    print(f"  Status: {result['status']}")

    # 5. Merge adapter
    print("\n[5] Merge Adapter")
    merged = engine.merge_adapter(adapter.adapter_id, "meta-llama/Llama-2-7b")
    print(f"  Merged model: {merged}")

    # 6. Adapter stats
    print(f"\n[6] Adapter Stats")
    print(f"  {engine.adapters.get_stats()}")

    # 7. Full engine stats
    print(f"\n[7] Engine Stats")
    print(f"  {engine.get_stats()}")

    # 8. Export
    print("\n[8] Export Report")
    engine.export_report("/tmp/finetune_report.json")
    print("  Exported to /tmp/finetune_report.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
