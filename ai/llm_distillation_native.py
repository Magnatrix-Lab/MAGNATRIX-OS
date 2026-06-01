"""Model Distillation — Teacher-student knowledge transfer, quantization, compression.

Modul ini menyediakan:
- DistillationEngine untuk transfer knowledge dari teacher ke student
- LayerPruner untuk pruning layer/head/neuron
- Quantizer untuk post-training quantization (INT8/INT4)
- CompressionPipeline untuk chaining compression techniques
- Capability evaluation pre/post distillation
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class QuantLevel(Enum):
    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"
    INT4 = "int4"


class PruneStrategy(Enum):
    MAGNITUDE = auto()
    ATTENTION_HEAD = auto()
    LAYER_DROP = auto()
    STRUCTURED = auto()


class DistillStatus(Enum):
    IDLE = auto()
    WARMUP = auto()
    DISTILLING = auto()
    PRUNING = auto()
    QUANTIZING = auto()
    EVALUATING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class ModelSpec:
    """Model specification with size and capability metrics."""
    model_id: str
    name: str
    param_count: int  # in millions
    layers: int
    hidden_dim: int
    attention_heads: int
    vocab_size: int
    quant: QuantLevel = QuantLevel.FP32
    metadata: Dict[str, Any] = field(default_factory=dict)

    def estimated_size_mb(self) -> float:
        bits_per_param = {"fp32": 32, "fp16": 16, "int8": 8, "int4": 4}
        return (self.param_count * 1e6 * bits_per_param.get(self.quant.value, 32)) / (8 * 1024 * 1024)


@dataclass
class DistillationConfig:
    """Configuration for distillation run."""
    temperature: float = 2.0
    alpha: float = 0.7  # weight for soft targets vs hard labels
    lr: float = 1e-4
    epochs: int = 5
    batch_size: int = 32
    prune_ratio: float = 0.0
    prune_strategy: Optional[PruneStrategy] = None
    quant: Optional[QuantLevel] = None


@dataclass
class DistillationResult:
    """Result of a distillation run."""
    run_id: str
    teacher_id: str
    student_id: str
    status: DistillStatus
    metrics: Dict[str, float]
    compression_ratio: float = 1.0
    speedup: float = 1.0
    accuracy_drop: float = 0.0
    teacher_size_mb: float = 0.0
    student_size_mb: float = 0.0
    duration: float = 0.0
    created_at: float = field(default_factory=time.time)


class DistillationEngine:
    """Transfer knowledge from teacher to smaller student."""

    def __init__(self, config: DistillationConfig):
        self.config = config
        self._status = DistillStatus.IDLE
        self._history: List[DistillationResult] = []

    def distill(self, teacher: ModelSpec, student: ModelSpec,
                train_fn: Optional[Callable[[ModelSpec, ModelSpec, DistillationConfig], Dict[str, float]]] = None) -> DistillationResult:
        self._status = DistillStatus.DISTILLING
        start = time.time()
        train_fn = train_fn or self._default_distill_fn
        metrics = train_fn(teacher, student, self.config)
        dur = time.time() - start

        # Calculate compression
        teacher_mb = teacher.estimated_size_mb()
        student_mb = student.estimated_size_mb()
        ratio = teacher_mb / max(student_mb, 1.0)
        acc_drop = max(0.0, metrics.get("teacher_acc", 0.9) - metrics.get("student_acc", 0.8))
        speedup = teacher.param_count / max(student.param_count, 1.0)

        result = DistillationResult(
            run_id=str(uuid.uuid4())[:12],
            teacher_id=teacher.model_id,
            student_id=student.model_id,
            status=DistillStatus.COMPLETED,
            metrics=metrics,
            compression_ratio=round(ratio, 2),
            speedup=round(speedup, 2),
            accuracy_drop=round(acc_drop, 4),
            teacher_size_mb=round(teacher_mb, 2),
            student_size_mb=round(student_mb, 2),
            duration=round(dur, 2)
        )
        self._history.append(result)
        self._status = DistillStatus.COMPLETED
        return result

    def _default_distill_fn(self, teacher: ModelSpec, student: ModelSpec, config: DistillationConfig) -> Dict[str, float]:
        # Simulated distillation: student accuracy approaches teacher with some gap
        teacher_acc = 0.90 + (uuid.uuid4().int % 50) / 1000
        student_acc = teacher_acc - (0.05 + (teacher.param_count - student.param_count) / 10000)
        loss = 0.3 + (teacher.param_count - student.param_count) / 50000
        return {
            "teacher_acc": round(teacher_acc, 4),
            "student_acc": round(max(0.5, student_acc), 4),
            "loss": round(loss, 4),
            "temperature": config.temperature,
            "alpha": config.alpha,
        }

    def get_status(self) -> DistillStatus:
        return self._status

    def get_history(self) -> List[DistillationResult]:
        return self._history


class LayerPruner:
    """Prune model layers, heads, or neurons."""

    def __init__(self, strategy: PruneStrategy = PruneStrategy.MAGNITUDE):
        self.strategy = strategy
        self._pruned_count = 0

    def prune(self, model: ModelSpec, ratio: float) -> ModelSpec:
        if ratio <= 0 or ratio >= 1.0:
            return model
        if self.strategy == PruneStrategy.LAYER_DROP:
            new_layers = max(1, int(model.layers * (1 - ratio)))
            new_params = int(model.param_count * (1 - ratio))
            self._pruned_count += model.layers - new_layers
            return ModelSpec(
                model_id=f"{model.model_id}-pruned",
                name=f"{model.name} (pruned)",
                param_count=new_params,
                layers=new_layers,
                hidden_dim=model.hidden_dim,
                attention_heads=max(1, int(model.attention_heads * (1 - ratio))),
                vocab_size=model.vocab_size,
                quant=model.quant
            )
        elif self.strategy == PruneStrategy.ATTENTION_HEAD:
            new_heads = max(1, int(model.attention_heads * (1 - ratio)))
            new_params = int(model.param_count * (1 - ratio * 0.2))
            self._pruned_count += model.attention_heads - new_heads
            return ModelSpec(
                model_id=f"{model.model_id}-headpruned",
                name=f"{model.name} (head-pruned)",
                param_count=new_params,
                layers=model.layers,
                hidden_dim=model.hidden_dim,
                attention_heads=new_heads,
                vocab_size=model.vocab_size,
                quant=model.quant
            )
        else:
            # Magnitude: just reduce param count proportionally
            new_params = int(model.param_count * (1 - ratio))
            self._pruned_count += 1
            return ModelSpec(
                model_id=f"{model.model_id}-pruned",
                name=f"{model.name} (pruned)",
                param_count=new_params,
                layers=model.layers,
                hidden_dim=model.hidden_dim,
                attention_heads=model.attention_heads,
                vocab_size=model.vocab_size,
                quant=model.quant
            )

    def get_stats(self) -> Dict[str, int]:
        return {"pruned_operations": self._pruned_count}


class Quantizer:
    """Post-training quantization to lower precision."""

    def __init__(self, target: QuantLevel = QuantLevel.INT8):
        self.target = target

    def quantize(self, model: ModelSpec) -> ModelSpec:
        return ModelSpec(
            model_id=f"{model.model_id}-{self.target.value}",
            name=f"{model.name} ({self.target.value})",
            param_count=model.param_count,
            layers=model.layers,
            hidden_dim=model.hidden_dim,
            attention_heads=model.attention_heads,
            vocab_size=model.vocab_size,
            quant=self.target
        )

    def estimated_accuracy_drop(self, from_q: QuantLevel, to_q: QuantLevel) -> float:
        drops = {
            ("fp32", "fp16"): 0.001,
            ("fp32", "int8"): 0.01,
            ("fp32", "int4"): 0.03,
            ("fp16", "int8"): 0.008,
            ("fp16", "int4"): 0.025,
            ("int8", "int4"): 0.015,
        }
        return drops.get((from_q.value, to_q.value), 0.02)


class CompressionPipeline:
    """Chain multiple compression techniques."""

    def __init__(self):
        self._steps: List[Tuple[str, Callable[[ModelSpec], ModelSpec]]] = []
        self._results: List[Dict[str, Any]] = []

    def add_prune(self, strategy: PruneStrategy, ratio: float) -> CompressionPipeline:
        pruner = LayerPruner(strategy)
        self._steps.append((f"prune-{strategy.name}", lambda m: pruner.prune(m, ratio)))
        return self

    def add_quantize(self, level: QuantLevel) -> CompressionPipeline:
        quantizer = Quantizer(level)
        self._steps.append((f"quantize-{level.value}", lambda m: quantizer.quantize(m)))
        return self

    def add_custom(self, name: str, fn: Callable[[ModelSpec], ModelSpec]) -> CompressionPipeline:
        self._steps.append((name, fn))
        return self

    def run(self, model: ModelSpec) -> Tuple[ModelSpec, List[Dict[str, Any]]]:
        current = model
        logs = []
        for name, fn in self._steps:
            before = current.estimated_size_mb()
            current = fn(current)
            after = current.estimated_size_mb()
            logs.append({
                "step": name,
                "before_mb": round(before, 2),
                "after_mb": round(after, 2),
                "ratio": round(before / max(after, 1.0), 2)
            })
        self._results.extend(logs)
        return current, logs

    def get_results(self) -> List[Dict[str, Any]]:
        return self._results


class DistillationBenchmark:
    """Evaluate teacher vs student capability retention."""

    def __init__(self):
        self._tasks: Dict[str, Callable[[ModelSpec], float]] = {}

    def add_task(self, name: str, eval_fn: Callable[[ModelSpec], float]) -> None:
        self._tasks[name] = eval_fn

    def evaluate(self, model: ModelSpec) -> Dict[str, float]:
        return {name: fn(model) for name, fn in self._tasks.items()}

    def compare(self, teacher: ModelSpec, student: ModelSpec) -> Dict[str, Any]:
        t_scores = self.evaluate(teacher)
        s_scores = self.evaluate(student)
        comparison = {}
        for task in self._tasks:
            comparison[task] = {
                "teacher": t_scores.get(task, 0.0),
                "student": s_scores.get(task, 0.0),
                "retention": round(s_scores.get(task, 0.0) / max(t_scores.get(task, 1e-9), 1e-9), 4)
            }
        return comparison

    @staticmethod
    def default() -> DistillationBenchmark:
        bench = DistillationBenchmark()
        bench.add_task("perplexity", lambda m: max(5.0, 20.0 - m.param_count / 1000))
        bench.add_task("throughput", lambda m: m.param_count / max(m.estimated_size_mb(), 1.0))
        bench.add_task("memory", lambda m: 100.0 / max(m.estimated_size_mb(), 1.0))
        return bench


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MODEL DISTILLATION DEMO")
    print("=" * 70)

    # 1. Teacher and student specs
    print("\n[1] Model Specifications")
    teacher = ModelSpec(
        model_id="t-llama-70b",
        name="Teacher LLaMA-70B",
        param_count=70_000,
        layers=80,
        hidden_dim=8192,
        attention_heads=64,
        vocab_size=32000
    )
    student = ModelSpec(
        model_id="s-llama-7b",
        name="Student LLaMA-7B",
        param_count=7_000,
        layers=32,
        hidden_dim=4096,
        attention_heads=32,
        vocab_size=32000
    )
    print(f"  Teacher: {teacher.param_count}M params, {teacher.estimated_size_mb():.1f} MB")
    print(f"  Student: {student.param_count}M params, {student.estimated_size_mb():.1f} MB")

    # 2. Distillation
    print("\n[2] Knowledge Distillation")
    config = DistillationConfig(temperature=2.5, alpha=0.7, epochs=3)
    engine = DistillationEngine(config)
    result = engine.distill(teacher, student)
    print(f"  Run: {result.run_id}")
    print(f"  Compression: {result.compression_ratio:.1f}x")
    print(f"  Speedup: {result.speedup:.1f}x")
    print(f"  Accuracy drop: {result.accuracy_drop:.2%}")
    print(f"  Metrics: {result.metrics}")
    print(f"  Duration: {result.duration}s")

    # 3. Pruning
    print("\n[3] Layer Pruning")
    pruner = LayerPruner(PruneStrategy.LAYER_DROP)
    pruned = pruner.prune(student, ratio=0.25)
    print(f"  Original: {student.layers} layers, {student.estimated_size_mb():.1f} MB")
    print(f"  Pruned: {pruned.layers} layers, {pruned.estimated_size_mb():.1f} MB")

    # 4. Quantization
    print("\n[4] Quantization")
    quantizer = Quantizer(QuantLevel.INT8)
    int8_model = quantizer.quantize(pruned)
    print(f"  INT8 model: {int8_model.estimated_size_mb():.1f} MB")
    print(f"  Accuracy drop (FP32->INT8): {quantizer.estimated_accuracy_drop(QuantLevel.FP32, QuantLevel.INT8):.2%}")

    quantizer4 = Quantizer(QuantLevel.INT4)
    int4_model = quantizer4.quantize(pruned)
    print(f"  INT4 model: {int4_model.estimated_size_mb():.1f} MB")
    print(f"  Accuracy drop (FP32->INT4): {quantizer.estimated_accuracy_drop(QuantLevel.FP32, QuantLevel.INT4):.2%}")

    # 5. Compression pipeline
    print("\n[5] Compression Pipeline")
    pipeline = CompressionPipeline()
    pipeline.add_prune(PruneStrategy.ATTENTION_HEAD, 0.2)
    pipeline.add_quantize(QuantLevel.INT8)
    final, logs = pipeline.run(teacher)
    print(f"  Steps: {len(logs)}")
    for log in logs:
        print(f"    {log['step']}: {log['before_mb']} MB -> {log['after_mb']} MB ({log['ratio']}x)")
    print(f"  Final: {final.name}, {final.estimated_size_mb():.1f} MB ({teacher.estimated_size_mb()/max(final.estimated_size_mb(),1):.1f}x compression)")

    # 6. Benchmark
    print("\n[6] Capability Benchmark")
    bench = DistillationBenchmark.default()
    t_scores = bench.evaluate(teacher)
    s_scores = bench.evaluate(student)
    print(f"  Teacher scores: {t_scores}")
    print(f"  Student scores: {s_scores}")
    comparison = bench.compare(teacher, student)
    print(f"  Retention:")
    for task, vals in comparison.items():
        print(f"    {task}: {vals['retention']:.1%} (teacher={vals['teacher']:.2f}, student={vals['student']:.2f})")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
