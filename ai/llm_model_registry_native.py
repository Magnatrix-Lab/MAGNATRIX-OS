"""Model Registry — Central catalog for LLM models, capabilities, and metadata.

Modul ini menyediakan:
- ModelRecord untuk metadata model (params, context, capabilities, pricing)
- CapabilityIndex untuk indexing model by capability tags
- ModelComparator untuk head-to-head comparison
- RegistryManager untuk CRUD dan discovery
- ModelRecommender untuk matching task ke model terbaik
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum, auto


class ModelCapability(Enum):
    CHAT = "chat"
    CODE = "code"
    REASONING = "reasoning"
    VISION = "vision"
    AUDIO = "audio"
    MULTILINGUAL = "multilingual"
    LONG_CONTEXT = "long_context"
    FUNCTION_CALLING = "function_calling"
    JSON_MODE = "json_mode"
    TOOL_USE = "tool_use"
    AGENTIC = "agentic"
    RAG = "rag"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"


class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    META = "meta"
    MISTRAL = "mistral"
    COHERE = "cohere"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class ModelPricing:
    input_per_1k: float = 0.0
    output_per_1k: float = 0.0
    currency: str = "USD"


@dataclass
class ModelRecord:
    """Complete model metadata record."""
    model_id: str
    name: str
    provider: ModelProvider
    param_count: Optional[int] = None  # in millions
    context_window: int = 4096
    capabilities: Set[ModelCapability] = field(default_factory=set)
    pricing: ModelPricing = field(default_factory=ModelPricing)
    languages: List[str] = field(default_factory=list)
    benchmarks: Dict[str, float] = field(default_factory=dict)  # benchmark_name -> score
    status: str = "active"  # active, deprecated, experimental, offline
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    last_used: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "provider": self.provider.value,
            "param_count": self.param_count,
            "context_window": self.context_window,
            "capabilities": [c.value for c in self.capabilities],
            "pricing": {
                "input_per_1k": self.pricing.input_per_1k,
                "output_per_1k": self.pricing.output_per_1k,
            },
            "languages": self.languages,
            "benchmarks": self.benchmarks,
            "status": self.status,
            "registered_at": self.registered_at,
        }

    def supports(self, capability: ModelCapability) -> bool:
        return capability in self.capabilities

    def has_language(self, lang: str) -> bool:
        return lang in self.languages or not self.languages

    def cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens / 1000.0) * self.pricing.input_per_1k + (output_tokens / 1000.0) * self.pricing.output_per_1k


class CapabilityIndex:
    """Index models by their capabilities."""

    def __init__(self):
        self._index: Dict[ModelCapability, Set[str]] = {c: set() for c in ModelCapability}
        self._language_index: Dict[str, Set[str]] = {}

    def add(self, model: ModelRecord) -> None:
        for cap in model.capabilities:
            self._index[cap].add(model.model_id)
        for lang in model.languages:
            self._language_index.setdefault(lang, set()).add(model.model_id)

    def remove(self, model: ModelRecord) -> None:
        for cap in model.capabilities:
            self._index[cap].discard(model.model_id)
        for lang in model.languages:
            self._language_index.get(lang, set()).discard(model.model_id)

    def find_by_capability(self, capability: ModelCapability) -> Set[str]:
        return self._index.get(capability, set())

    def find_by_capabilities(self, capabilities: List[ModelCapability], match_all: bool = True) -> Set[str]:
        if not capabilities:
            return set()
        results = [self._index.get(c, set()) for c in capabilities]
        if match_all:
            return set.intersection(*results) if results else set()
        return set.union(*results) if results else set()

    def find_by_language(self, language: str) -> Set[str]:
        return self._language_index.get(language, set())


class ModelComparator:
    """Compare models head-to-head."""

    def compare(self, model_a: ModelRecord, model_b: ModelRecord, dimensions: Optional[List[str]] = None) -> Dict[str, Any]:
        dims = dimensions or ["context_window", "cost", "benchmarks"]
        comparison = {}

        if "context_window" in dims:
            comparison["context_window"] = {
                "a": model_a.context_window,
                "b": model_b.context_window,
                "winner": "a" if model_a.context_window > model_b.context_window else "b" if model_b.context_window > model_a.context_window else "tie"
            }

        if "cost" in dims:
            a_cost = model_a.pricing.input_per_1k + model_a.pricing.output_per_1k
            b_cost = model_b.pricing.input_per_1k + model_b.pricing.output_per_1k
            comparison["cost"] = {
                "a": a_cost,
                "b": b_cost,
                "winner": "a" if a_cost < b_cost else "b" if b_cost < a_cost else "tie"
            }

        if "benchmarks" in dims:
            common = set(model_a.benchmarks.keys()) & set(model_b.benchmarks.keys())
            bench_comparison = {}
            for bench in common:
                a_score = model_a.benchmarks[bench]
                b_score = model_b.benchmarks[bench]
                bench_comparison[bench] = {
                    "a": a_score,
                    "b": b_score,
                    "winner": "a" if a_score > b_score else "b" if b_score > a_score else "tie"
                }
            comparison["benchmarks"] = bench_comparison

        return comparison

    def rank(self, models: List[ModelRecord], criterion: str = "cost") -> List[Tuple[ModelRecord, Any]]:
        if criterion == "cost":
            return sorted(models, key=lambda m: m.pricing.input_per_1k + m.pricing.output_per_1k)
        elif criterion == "context":
            return sorted(models, key=lambda m: m.context_window, reverse=True)
        elif criterion.startswith("benchmark:"):
            bench = criterion.split(":", 1)[1]
            return sorted(models, key=lambda m: m.benchmarks.get(bench, 0), reverse=True)
        return models


class RegistryManager:
    """Central model registry with CRUD and discovery."""

    def __init__(self):
        self._models: Dict[str, ModelRecord] = {}
        self._capability_index = CapabilityIndex()
        self._comparator = ModelComparator()
        self._filters: List[Callable[[ModelRecord], bool]] = []

    def register(self, model: ModelRecord) -> ModelRecord:
        self._models[model.model_id] = model
        self._capability_index.add(model)
        return model

    def unregister(self, model_id: str) -> bool:
        model = self._models.pop(model_id, None)
        if model:
            self._capability_index.remove(model)
            return True
        return False

    def get(self, model_id: str) -> Optional[ModelRecord]:
        return self._models.get(model_id)

    def find(self, **criteria) -> List[ModelRecord]:
        results = list(self._models.values())
        if "provider" in criteria:
            results = [m for m in results if m.provider.value == criteria["provider"]]
        if "capability" in criteria:
            cap = ModelCapability(criteria["capability"])
            results = [m for m in results if m.supports(cap)]
        if "capabilities" in criteria:
            caps = [ModelCapability(c) for c in criteria["capabilities"]]
            results = [m for m in results if all(m.supports(c) for c in caps)]
        if "language" in criteria:
            results = [m for m in results if m.has_language(criteria["language"])]
        if "status" in criteria:
            results = [m for m in results if m.status == criteria["status"]]
        if "max_cost_per_1k" in criteria:
            max_cost = criteria["max_cost_per_1k"]
            results = [m for m in results if m.pricing.input_per_1k + m.pricing.output_per_1k <= max_cost]
        for f in self._filters:
            results = [m for m in results if f(m)]
        return results

    def compare(self, model_id_a: str, model_id_b: str, dimensions: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        a = self._models.get(model_id_a)
        b = self._models.get(model_id_b)
        if not a or not b:
            return None
        return self._comparator.compare(a, b, dimensions)

    def rank(self, criterion: str = "cost") -> List[ModelRecord]:
        return self._comparator.rank(list(self._models.values()), criterion)

    def list_all(self) -> List[ModelRecord]:
        return list(self._models.values())

    def get_stats(self) -> Dict[str, Any]:
        by_provider: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        for m in self._models.values():
            by_provider[m.provider.value] = by_provider.get(m.provider.value, 0) + 1
            by_status[m.status] = by_status.get(m.status, 0) + 1
        return {
            "total_models": len(self._models),
            "by_provider": by_provider,
            "by_status": by_status,
            "capabilities_indexed": {k.value: len(v) for k, v in self._capability_index._index.items()},
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in self._models.values()], f, indent=2)

    def add_filter(self, fn: Callable[[ModelRecord], bool]) -> None:
        self._filters.append(fn)


class ModelRecommender:
    """Recommend best model for a given task."""

    def __init__(self, registry: RegistryManager):
        self.registry = registry
        self._task_mappings: Dict[str, List[ModelCapability]] = {
            "chat": [ModelCapability.CHAT],
            "coding": [ModelCapability.CODE, ModelCapability.CHAT],
            "analysis": [ModelCapability.REASONING, ModelCapability.CHAT],
            "image_description": [ModelCapability.VISION, ModelCapability.CHAT],
            "translation": [ModelCapability.TRANSLATION, ModelCapability.MULTILINGUAL],
            "summarization": [ModelCapability.SUMMARIZATION, ModelCapability.LONG_CONTEXT],
            "rag": [ModelCapability.RAG, ModelCapability.LONG_CONTEXT],
            "agent": [ModelCapability.AGENTIC, ModelCapability.TOOL_USE, ModelCapability.FUNCTION_CALLING],
            "json_output": [ModelCapability.JSON_MODE, ModelCapability.CHAT],
        }

    def recommend(self, task: str, language: str = "en", max_cost: Optional[float] = None,
                  top_k: int = 3) -> List[Tuple[ModelRecord, float]]:
        required_caps = self._task_mappings.get(task, [ModelCapability.CHAT])
        candidates = self.registry.find(capabilities=[c.value for c in required_caps], status="active")
        if language:
            candidates = [c for c in candidates if c.has_language(language)]
        if max_cost is not None:
            candidates = [c for c in candidates if c.pricing.input_per_1k + c.pricing.output_per_1k <= max_cost]

        # Score candidates
        scored = []
        for model in candidates:
            score = 0.0
            # Capability match score
            for cap in required_caps:
                if model.supports(cap):
                    score += 1.0
            # Cost efficiency bonus
            total_cost = model.pricing.input_per_1k + model.pricing.output_per_1k
            if total_cost > 0:
                score += 1.0 / (total_cost + 0.001)
            else:
                score += 2.0  # Free models get bonus
            # Context window bonus
            score += model.context_window / 10000.0
            scored.append((model, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def add_task_mapping(self, task: str, capabilities: List[ModelCapability]) -> None:
        self._task_mappings[task] = capabilities


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MODEL REGISTRY DEMO")
    print("=" * 70)

    registry = RegistryManager()

    # 1. Register models
    print("\n[1] Register Models")
    models = [
        ModelRecord("gpt-4o", "GPT-4o", ModelProvider.OPENAI, param_count=200, context_window=128000,
                    capabilities={ModelCapability.CHAT, ModelCapability.VISION, ModelCapability.CODE, ModelCapability.TOOL_USE, ModelCapability.JSON_MODE},
                    pricing=ModelPricing(0.005, 0.015), languages=["en", "es", "fr", "de", "zh"],
                    benchmarks={"mmlu": 0.887, "human_eval": 0.90}),
        ModelRecord("gpt-4o-mini", "GPT-4o Mini", ModelProvider.OPENAI, param_count=8, context_window=128000,
                    capabilities={ModelCapability.CHAT, ModelCapability.VISION, ModelCapability.CODE, ModelCapability.JSON_MODE},
                    pricing=ModelPricing(0.00015, 0.0006), languages=["en"],
                    benchmarks={"mmlu": 0.82, "human_eval": 0.87}),
        ModelRecord("claude-3-5-sonnet", "Claude 3.5 Sonnet", ModelProvider.ANTHROPIC, param_count=175, context_window=200000,
                    capabilities={ModelCapability.CHAT, ModelCapability.VISION, ModelCapability.CODE, ModelCapability.TOOL_USE, ModelCapability.LONG_CONTEXT},
                    pricing=ModelPricing(0.003, 0.015), languages=["en", "es", "fr", "ja"],
                    benchmarks={"mmlu": 0.89, "human_eval": 0.92}),
        ModelRecord("llama-3-70b", "LLaMA 3 70B", ModelProvider.LOCAL, param_count=70, context_window=8192,
                    capabilities={ModelCapability.CHAT, ModelCapability.CODE, ModelCapability.RAG},
                    pricing=ModelPricing(0.0, 0.0), languages=["en"]),
    ]
    for m in models:
        registry.register(m)
        print(f"  {m.name:25} {m.provider.value:10} {m.param_count}M params ${m.pricing.input_per_1k+m.pricing.output_per_1k:.4f}/1K")

    # 2. Find by capability
    print("\n[2] Find by Capability")
    vision_models = registry.find(capability="vision", status="active")
    print(f"  Vision models: {[m.name for m in vision_models]}")
    code_models = registry.find(capabilities=["code", "tool_use"], status="active")
    print(f"  Code+Tool models: {[m.name for m in code_models]}")

    # 3. Compare
    print("\n[3] Model Comparison")
    comp = registry.compare("gpt-4o", "claude-3-5-sonnet", ["context_window", "cost", "benchmarks"])
    if comp:
        for dim, result in comp.items():
            print(f"  {dim}: {result}")

    # 4. Rank
    print("\n[4] Rank by Cost")
    ranked = registry.rank("cost")
    for m in ranked:
        total = m.pricing.input_per_1k + m.pricing.output_per_1k
        print(f"  {m.name:25} ${total:.4f}/1K")

    # 5. Recommend
    print("\n[5] Model Recommendation")
    recommender = ModelRecommender(registry)
    for task in ["coding", "agent", "translation", "chat"]:
        recs = recommender.recommend(task, top_k=2)
        print(f"  {task:15} -> {', '.join(f'{m.name} (score={s:.2f})' for m, s in recs)}")

    # 6. Cost estimation
    print("\n[6] Cost Estimation")
    for m in models:
        cost = m.cost_estimate(2000, 500)
        print(f"  {m.name:25} 2000in + 500out = ${cost:.6f}")

    # 7. Stats
    print("\n[7] Registry Stats")
    stats = registry.get_stats()
    print(f"  Total: {stats['total_models']}")
    print(f"  By provider: {stats['by_provider']}")
    print(f"  By status: {stats['by_status']}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
