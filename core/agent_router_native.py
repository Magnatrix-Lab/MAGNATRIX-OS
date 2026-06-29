"""
agent_router_native.py
MAGNATRIX-OS — Agent Router

Inspired by arXiv 2606.22902: Agent-as-a-Router with C-A-F loop for coding tasks. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class RoutingDecision:
    decision_id: str
    task: str
    selected_model: str
    context: str
    action: str
    feedback: str
    confidence: float


class AgentRouter:
    """Agent-as-a-Router with Context-Action-Feedback loop."""

    def __init__(self, cache_dir: str = "./agent_router"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.decisions: Dict[str, RoutingDecision] = {}
        self.model_scores: Dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["decisions.json", "scores.json"]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "decisions.json":
                            for did, dd in data.items():
                                self.decisions[did] = RoutingDecision(**dd)
                        else:
                            self.model_scores = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.cache_dir / "decisions.json", "w", encoding="utf-8") as f:
            json.dump({did: asdict(d) for did, d in self.decisions.items()}, f, indent=2)
        with open(self.cache_dir / "scores.json", "w", encoding="utf-8") as f:
            json.dump(self.model_scores, f, indent=2)

    def route(self, decision_id: str, task: str, available_models: List[str]) -> RoutingDecision:
        """Route task to best model using C-A-F loop."""
        # Context: analyze task
        context = f"Task: {task[:50]}..."

        # Action: select best model based on scores
        best_model = None
        best_score = -1
        for model in available_models:
            score = self.model_scores.get(model, 0.5)
            if score > best_score:
                best_score = score
                best_model = model

        if not best_model:
            best_model = available_models[0] if available_models else "none"

        decision = RoutingDecision(
            decision_id=decision_id, task=task, selected_model=best_model,
            context=context, action=f"route_to_{best_model}", feedback="pending", confidence=round(best_score, 2),
        )
        self.decisions[decision_id] = decision
        self._save()
        return decision

    def feedback(self, decision_id: str, success: bool) -> None:
        decision = self.decisions.get(decision_id)
        if decision:
            decision.feedback = "success" if success else "failure"
            # Update model score
            current = self.model_scores.get(decision.selected_model, 0.5)
            delta = 0.05 if success else -0.05
            self.model_scores[decision.selected_model] = max(0.0, min(1.0, current + delta))
            self._save()

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.decisions)
        successful = sum(1 for d in self.decisions.values() if d.feedback == "success")
        return {"total_routes": total, "successful": successful, "models_tracked": len(self.model_scores)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgentRouter", "RoutingDecision"]