"""Agents Model Selector - Model selection and optimization for ADK agents."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ModelProfile:
    model_id: str
    name: str
    provider: str = "google"
    capabilities: List[str] = field(default_factory=list)
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    context_window: int = 8192
    latency_ms_avg: float = 0.0
    quality_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "provider": self.provider,
            "capabilities": self.capabilities,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "context_window": self.context_window,
            "latency_ms_avg": self.latency_ms_avg,
            "quality_score": self.quality_score,
        }


@dataclass
class SelectionDecision:
    decision_id: str
    task_type: str
    selected_model: str
    reasoning: str = ""
    estimated_cost: float = 0.0
    confidence: float = 0.0
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "decision_id": self.decision_id,
            "task_type": self.task_type,
            "selected_model": self.selected_model,
            "reasoning": self.reasoning,
            "estimated_cost": self.estimated_cost,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


class AgentsModelSelector:
    """Model selection and optimization for ADK agent workloads."""

    MODEL_CATALOG = [
        ModelProfile("gemini-2.0-flash", "Gemini 2.0 Flash", "google", ["chat", "coding", "analysis"], 0.075, 0.30, 1000000, 200, 0.85),
        ModelProfile("gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite", "google", ["chat", "quick"], 0.0375, 0.15, 1000000, 150, 0.75),
        ModelProfile("gemini-2.5-pro", "Gemini 2.5 Pro", "google", ["chat", "coding", "reasoning", "analysis"], 1.25, 5.00, 1000000, 500, 0.95),
        ModelProfile("gemini-2.5-flash", "Gemini 2.5 Flash", "google", ["chat", "coding", "analysis"], 0.15, 0.60, 1000000, 250, 0.88),
        ModelProfile("gemini-1.5-pro", "Gemini 1.5 Pro", "google", ["chat", "coding", "analysis"], 1.25, 5.00, 2000000, 400, 0.90),
    ]

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "agents_model_selector"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.models: Dict[str, ModelProfile] = {}
        self.decisions: List[SelectionDecision] = []
        self._init_catalog()
        self._load_state()

    def _init_catalog(self) -> None:
        for m in self.MODEL_CATALOG:
            self.models[m.model_id] = m

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for d in data.get("decisions", []):
                    self.decisions.append(SelectionDecision(**d))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "models": [m.to_dict() for m in self.models.values()],
            "decisions": [d.to_dict() for d in self.decisions],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def select(self, task_type: str, budget_priority: bool = False, quality_priority: bool = False, latency_priority: bool = False) -> SelectionDecision:
        """Select optimal model for task."""
        candidates = [m for m in self.models.values() if task_type in m.capabilities]
        if not candidates:
            candidates = list(self.models.values())

        if budget_priority:
            candidates.sort(key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output)
        elif quality_priority:
            candidates.sort(key=lambda m: m.quality_score, reverse=True)
        elif latency_priority:
            candidates.sort(key=lambda m: m.latency_ms_avg)
        else:
            candidates.sort(key=lambda m: m.quality_score / (m.cost_per_1k_input + 0.001), reverse=True)

        selected = candidates[0] if candidates else self.MODEL_CATALOG[0]
        reasoning = f"Selected {selected.name} based on "
        if budget_priority:
            reasoning += "cost optimization"
        elif quality_priority:
            reasoning += "quality maximization"
        elif latency_priority:
            reasoning += "latency minimization"
        else:
            reasoning += "quality/cost ratio"
        reasoning += f" for task '{task_type}'"

        decision = SelectionDecision(
            decision_id=f"dec_{task_type}_{int(time.time())}",
            task_type=task_type,
            selected_model=selected.model_id,
            reasoning=reasoning,
            estimated_cost=round((selected.cost_per_1k_input + selected.cost_per_1k_output) * 2, 4),
            confidence=round(selected.quality_score, 2),
            timestamp=time.time(),
        )
        self.decisions.append(decision)
        self._save_state()
        return decision

    def recommend_for_agent(self, agent_capabilities: List[str]) -> List[ModelProfile]:
        """Recommend models for an agent based on capabilities."""
        scores = {}
        for cap in agent_capabilities:
            for model in self.models.values():
                if cap in model.capabilities:
                    scores[model.model_id] = scores.get(model.model_id, 0) + model.quality_score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [self.models[mid] for mid, _ in ranked[:3]]

    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a model usage."""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        model = self.models[model_id]
        return round((input_tokens / 1000.0) * model.cost_per_1k_input + (output_tokens / 1000.0) * model.cost_per_1k_output, 4)

    def compare_models(self, model_ids: List[str]) -> List[Dict]:
        """Compare models across dimensions."""
        comparison = []
        for mid in model_ids:
            if mid in self.models:
                m = self.models[mid]
                comparison.append({
                    "model_id": mid,
                    "name": m.name,
                    "cost_total_1k": round(m.cost_per_1k_input + m.cost_per_1k_output, 4),
                    "context_window": m.context_window,
                    "latency_ms": m.latency_ms_avg,
                    "quality_score": m.quality_score,
                    "capabilities": m.capabilities,
                })
        return comparison

    def add_model(self, model_id: str, name: str, provider: str, capabilities: List[str], cost_in: float, cost_out: float, context: int) -> ModelProfile:
        model = ModelProfile(model_id=model_id, name=name, provider=provider, capabilities=capabilities, cost_per_1k_input=cost_in, cost_per_1k_output=cost_out, context_window=context)
        self.models[model_id] = model
        self._save_state()
        return model

    def get_stats(self) -> Dict:
        avg_quality = sum(m.quality_score for m in self.models.values()) / max(1, len(self.models))
        avg_cost = sum(m.cost_per_1k_input + m.cost_per_1k_output for m in self.models.values()) / max(1, len(self.models))
        return {
            "models_cataloged": len(self.models),
            "decisions_made": len(self.decisions),
            "avg_quality_score": round(avg_quality, 3),
            "avg_cost_per_1k": round(avg_cost, 4),
        }

    def to_dict(self) -> Dict:
        return {
            "models": [m.to_dict() for m in self.models.values()],
            "decisions": [d.to_dict() for d in self.decisions],
            "stats": self.get_stats(),
        }


__all__ = ["AgentsModelSelector", "ModelProfile", "SelectionDecision"]
