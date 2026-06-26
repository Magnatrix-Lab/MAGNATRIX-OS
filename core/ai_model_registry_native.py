#!/usr/bin/env python3
"""
AI Model Registry for MAGNATRIX-OS
Model catalog, benchmark scoring, model lifecycle (register → evaluate → deploy → retire).
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ModelSpec:
    """Specification of an AI model."""
    id: str
    name: str
    version: str
    provider: str  # local, ollama, openai, anthropic, google
    model_type: str  # llm, embedding, vision, audio, multimodal
    size_mb: float = 0.0
    parameters: str = ""
    quantization: str = ""
    context_length: int = 4096
    description: str = ""
    tags: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    license: str = ""
    source_url: str = ""
    local_path: str = ""
    api_endpoint: str = ""
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of benchmarking a model."""
    model_id: str
    benchmark: str
    score: float
    latency_ms: float
    throughput_tokens_per_sec: float
    memory_mb: float
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelLifecycle:
    """Lifecycle state of a model."""
    model_id: str
    state: str = "registered"  # registered, evaluating, ready, deployed, deprecated, retired
    registered_at: float = field(default_factory=time.time)
    evaluated_at: float = 0.0
    deployed_at: float = 0.0
    retired_at: float = 0.0
    deployment_count: int = 0
    error_count: int = 0


class ModelRegistry:
    """Central registry for all AI models."""

    DEFAULT_MODELS = [
        ModelSpec(
            id="qwen2.5-7b",
            name="Qwen 2.5 7B",
            version="2.5",
            provider="ollama",
            model_type="llm",
            size_mb=4500,
            parameters="7B",
            quantization="Q4_K_M",
            context_length=32768,
            description="Alibaba Qwen 2.5 — strong multilingual reasoning",
            tags=["multilingual", "reasoning", "lightweight"],
            capabilities=["chat", "code", "analysis"],
        ),
        ModelSpec(
            id="llama3.2-3b",
            name="Llama 3.2 3B",
            version="3.2",
            provider="ollama",
            model_type="llm",
            size_mb=2000,
            parameters="3B",
            quantization="Q4_K_M",
            context_length=128000,
            description="Meta Llama 3.2 — fast, efficient",
            tags=["fast", "efficient", "mobile"],
            capabilities=["chat", "summarization"],
        ),
        ModelSpec(
            id="phi-4",
            name="Phi-4",
            version="4",
            provider="ollama",
            model_type="llm",
            size_mb=9000,
            parameters="14B",
            quantization="Q4_K_M",
            context_length=16384,
            description="Microsoft Phi-4 — strong reasoning",
            tags=["reasoning", "math", "code"],
            capabilities=["chat", "code", "math"],
        ),
        ModelSpec(
            id="mistral-7b",
            name="Mistral 7B",
            version="0.3",
            provider="ollama",
            model_type="llm",
            size_mb=4500,
            parameters="7B",
            quantization="Q4_K_M",
            context_length=32768,
            description="Mistral 7B v0.3 — balanced performance",
            tags=["balanced", "general"],
            capabilities=["chat", "code", "analysis"],
        ),
        ModelSpec(
            id="deepseek-r1-7b",
            name="DeepSeek R1 7B",
            version="1",
            provider="ollama",
            model_type="llm",
            size_mb=4700,
            parameters="7B",
            quantization="Q4_K_M",
            context_length=32768,
            description="DeepSeek R1 — reasoning specialist",
            tags=["reasoning", "chain-of-thought"],
            capabilities=["chat", "reasoning", "math"],
        ),
        ModelSpec(
            id="gemma2-9b",
            name="Gemma 2 9B",
            version="2",
            provider="ollama",
            model_type="llm",
            size_mb=5500,
            parameters="9B",
            quantization="Q4_K_M",
            context_length=8192,
            description="Google Gemma 2 — open, capable",
            tags=["open", "google", "general"],
            capabilities=["chat", "code", "analysis"],
        ),
    ]

    def __init__(self, store_dir: str = "./data/models") -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._models: Dict[str, ModelSpec] = {}
        self._benchmarks: Dict[str, List[BenchmarkResult]] = {}
        self._lifecycles: Dict[str, ModelLifecycle] = {}
        self._active_model: Optional[str] = None
        self._load_defaults()

    def _load_defaults(self) -> None:
        for model in self.DEFAULT_MODELS:
            self._models[model.id] = model
            self._lifecycles[model.id] = ModelLifecycle(model_id=model.id)

    def register(self, spec: ModelSpec) -> bool:
        self._models[spec.id] = spec
        self._lifecycles[spec.id] = ModelLifecycle(model_id=spec.id)
        self._persist()
        return True

    def get(self, model_id: str) -> Optional[ModelSpec]:
        return self._models.get(model_id)

    def list_models(self, provider: Optional[str] = None, model_type: Optional[str] = None) -> List[ModelSpec]:
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        return models

    def add_benchmark(self, result: BenchmarkResult) -> None:
        if result.model_id not in self._benchmarks:
            self._benchmarks[result.model_id] = []
        self._benchmarks[result.model_id].append(result)

    def get_benchmarks(self, model_id: str) -> List[BenchmarkResult]:
        return self._benchmarks.get(model_id, [])

    def get_best_model(self, benchmark: str = "overall") -> Optional[ModelSpec]:
        """Get the best model by benchmark score."""
        best = None
        best_score = -1
        for model_id, results in self._benchmarks.items():
            for r in results:
                if r.benchmark == benchmark and r.score > best_score:
                    best_score = r.score
                    best = self._models.get(model_id)
        return best

    def compare_models(self, model_ids: List[str], benchmark: str = "overall") -> List[Dict[str, Any]]:
        """Compare multiple models on a benchmark."""
        results = []
        for mid in model_ids:
            model = self._models.get(mid)
            if not model:
                continue
            bench = self._benchmarks.get(mid, [])
            scores = [r.score for r in bench if r.benchmark == benchmark]
            avg_score = sum(scores) / len(scores) if scores else 0
            results.append({
                "model_id": mid,
                "name": model.name,
                "score": avg_score,
                "benchmarks": len(scores),
            })
        return sorted(results, key=lambda x: x["score"], reverse=True)

    def set_active(self, model_id: str) -> bool:
        if model_id not in self._models:
            return False
        self._active_model = model_id
        lifecycle = self._lifecycles.get(model_id)
        if lifecycle:
            lifecycle.state = "deployed"
            lifecycle.deployed_at = time.time()
            lifecycle.deployment_count += 1
        return True

    def get_active(self) -> Optional[ModelSpec]:
        if self._active_model:
            return self._models.get(self._active_model)
        return None

    def transition(self, model_id: str, new_state: str) -> bool:
        lifecycle = self._lifecycles.get(model_id)
        if not lifecycle:
            return False
        valid_transitions = {
            "registered": ["evaluating", "deprecated"],
            "evaluating": ["ready", "registered"],
            "ready": ["deployed", "deprecated"],
            "deployed": ["deprecated", "retired"],
            "deprecated": ["retired"],
            "retired": [],
        }
        if new_state not in valid_transitions.get(lifecycle.state, []):
            return False
        lifecycle.state = new_state
        if new_state == "evaluating":
            lifecycle.evaluated_at = time.time()
        elif new_state == "deployed":
            lifecycle.deployed_at = time.time()
        elif new_state == "retired":
            lifecycle.retired_at = time.time()
        self._persist()
        return True

    def recommend_for_task(self, task: str) -> List[ModelSpec]:
        """Recommend models for a specific task."""
        task_lower = task.lower()
        scored = []
        for model in self._models.values():
            score = 0
            for cap in model.capabilities:
                if cap.lower() in task_lower:
                    score += 2
            for tag in model.tags:
                if tag.lower() in task_lower:
                    score += 1
            if task_lower in model.description.lower():
                score += 3
            scored.append((score, model))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for s, m in scored[:5]]

    def _persist(self) -> None:
        data = {
            "models": [m.__dict__ for m in self._models.values()],
            "lifecycles": [{**l.__dict__} for l in self._lifecycles.values()],
            "active_model": self._active_model,
        }
        (self.store_dir / "registry.json").write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def stats(self) -> Dict[str, Any]:
        states = {}
        for l in self._lifecycles.values():
            states[l.state] = states.get(l.state, 0) + 1
        return {
            "total_models": len(self._models),
            "providers": len(set(m.provider for m in self._models.values())),
            "model_types": len(set(m.model_type for m in self._models.values())),
            "benchmarks": sum(len(v) for v in self._benchmarks.values()),
            "lifecycle_states": states,
            "active_model": self._active_model,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== AI Model Registry Demo ===\n")
    registry = ModelRegistry()

    print(f"Registered models: {len(registry.list_models())}")
    print(f"Providers: {set(m.provider for m in registry.list_models())}")

    # Add benchmarks
    for mid in ["qwen2.5-7b", "llama3.2-3b", "phi-4"]:
        registry.add_benchmark(BenchmarkResult(
            model_id=mid, benchmark="overall", score=85 + hash(mid) % 10,
            latency_ms=100, throughput_tokens_per_sec=50, memory_mb=5000, timestamp=time.time(),
        ))

    print(f"\nBest model: {registry.get_best_model('overall')}")
    print(f"\nComparison:")
    for c in registry.compare_models(["qwen2.5-7b", "llama3.2-3b", "phi-4"], "overall"):
        print(f"  {c['name']}: {c['score']:.1f}")

    print(f"\nRecommend for 'coding':")
    for m in registry.recommend_for_task("coding"):
        print(f"  {m.name} ({m.id}) - {m.capabilities}")

    registry.set_active("qwen2.5-7b")
    print(f"\nActive: {registry.get_active()}")
    print(f"Stats: {registry.stats()}")


if __name__ == "__main__":
    _demo()
