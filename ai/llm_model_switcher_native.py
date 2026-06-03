"""LLM Model Switcher — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class ModelCapability(Enum):
    REASONING = auto()
    CODING = auto()
    CREATIVITY = auto()
    SPEED = auto()

@dataclass
class ModelProfile:
    id: str
    name: str
    capabilities: Dict[ModelCapability, float] = field(default_factory=dict)
    cost_per_token: float = 0.0
    max_tokens: int = 4096

class ModelSwitcher:
    def __init__(self) -> None:
        self._models: Dict[str, ModelProfile] = {}
        self._fallback_chain: List[str] = []

    def register(self, model: ModelProfile) -> None:
        self._models[model.id] = model

    def set_fallback_chain(self, chain: List[str]) -> None:
        self._fallback_chain = chain

    def select(self, required_capabilities: Dict[ModelCapability, float]) -> Optional[ModelProfile]:
        scored = []
        for mid, model in self._models.items():
            score = 0.0
            for cap, min_score in required_capabilities.items():
                model_score = model.capabilities.get(cap, 0.0)
                if model_score < min_score:
                    score = -1.0
                    break
                score += model_score
            if score >= 0:
                scored.append((score, model))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None

    def fallback(self, failed_model_id: str) -> Optional[ModelProfile]:
        for mid in self._fallback_chain:
            if mid != failed_model_id and mid in self._models:
                return self._models[mid]
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {"models": len(self._models), "fallback_chain": self._fallback_chain}

def run() -> None:
    print("Model Switcher test")
    e = ModelSwitcher()
    e.register(ModelProfile("m1", "FastModel", {ModelCapability.SPEED: 0.9, ModelCapability.REASONING: 0.5}, 0.001, 2048))
    e.register(ModelProfile("m2", "SmartModel", {ModelCapability.REASONING: 0.95, ModelCapability.CODING: 0.9, ModelCapability.SPEED: 0.4}, 0.005, 8192))
    e.register(ModelProfile("m3", "CreativeModel", {ModelCapability.CREATIVITY: 0.95, ModelCapability.REASONING: 0.6}, 0.003, 4096))
    e.set_fallback_chain(["m2", "m3", "m1"])
    selected = e.select({ModelCapability.REASONING: 0.8, ModelCapability.CODING: 0.8})
    print("  Selected for reasoning+coding: " + (selected.name if selected else "None"))
    selected2 = e.select({ModelCapability.SPEED: 0.95})
    print("  Selected for speed: " + (selected2.name if selected2 else "None"))
    fb = e.fallback("m2")
    print("  Fallback from m2: " + (fb.name if fb else "None"))
    print("Model Switcher test complete.")

if __name__ == "__main__":
    run()
