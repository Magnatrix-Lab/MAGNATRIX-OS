"""Model Ensemble — Combine multiple models for improved accuracy and robustness.

Modul ini menyediakan:
- EnsembleMember untuk single model dalam ensemble
- VotingEngine untuk majority/weighted voting
- StackingEnsemble untuk stacked generalization
- EnsembleRouter untuk route to best model
- EnsembleEngine untuk manage ensembles
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class VoteStrategy(Enum):
    MAJORITY = auto()
    WEIGHTED = auto()
    AVERAGE = auto()
    CONFIDENCE = auto()


@dataclass
class EnsembleMember:
    """Single model in ensemble."""
    member_id: str
    name: str
    predict_fn: Optional[Callable[[str], str]] = None
    weight: float = 1.0
    accuracy: float = 0.5
    latency_ms: float = 100.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def predict(self, input_text: str) -> str:
        if self.predict_fn:
            return self.predict_fn(input_text)
        return f"[{self.name}] prediction"


@dataclass
class EnsemblePrediction:
    """Prediction result from ensemble."""
    prediction_id: str
    input_text: str
    predictions: Dict[str, str] = field(default_factory=dict)
    final_output: str = ""
    confidence: float = 0.0
    strategy: str = ""


class VotingEngine:
    """Vote-based ensemble."""

    def vote(self, predictions: Dict[str, str], weights: Optional[Dict[str, float]] = None, strategy: VoteStrategy = VoteStrategy.WEIGHTED) -> Tuple[str, float]:
        if not predictions:
            return "", 0.0
        weights = weights or {k: 1.0 for k in predictions}
        if strategy == VoteStrategy.MAJORITY:
            return self._majority_vote(predictions)
        elif strategy == VoteStrategy.WEIGHTED:
            return self._weighted_vote(predictions, weights)
        elif strategy == VoteStrategy.CONFIDENCE:
            return self._confidence_vote(predictions, weights)
        return self._average_vote(predictions)

    def _majority_vote(self, predictions: Dict[str, str]) -> Tuple[str, float]:
        counts: Dict[str, int] = {}
        for p in predictions.values():
            counts[p] = counts.get(p, 0) + 1
        winner = max(counts, key=counts.get)
        confidence = counts[winner] / len(predictions)
        return winner, confidence

    def _weighted_vote(self, predictions: Dict[str, str], weights: Dict[str, float]) -> Tuple[str, float]:
        scores: Dict[str, float] = {}
        for model_id, pred in predictions.items():
            w = weights.get(model_id, 1.0)
            scores[pred] = scores.get(pred, 0.0) + w
        winner = max(scores, key=scores.get)
        total = sum(scores.values())
        confidence = scores[winner] / total if total > 0 else 0.0
        return winner, confidence

    def _confidence_vote(self, predictions: Dict[str, str], weights: Dict[str, float]) -> Tuple[str, float]:
        return self._weighted_vote(predictions, weights)

    def _average_vote(self, predictions: Dict[str, str]) -> Tuple[str, float]:
        # For text: just return concatenated or first
        if not predictions:
            return "", 0.0
        return list(predictions.values())[0], 1.0 / len(predictions)


class StackingEnsemble:
    """Stacked generalization ensemble."""

    def __init__(self, meta_learner: Optional[Callable[[Dict[str, str]], str]] = None):
        self.meta_learner = meta_learner or self._default_meta
        self._base_predictions: List[Dict[str, Any]] = []

    def predict(self, input_text: str, members: List[EnsembleMember]) -> str:
        base_preds = {m.member_id: m.predict(input_text) for m in members if m.enabled}
        return self.meta_learner(base_preds)

    def _default_meta(self, predictions: Dict[str, str]) -> str:
        # Combine all predictions into one response
        return " | ".join(predictions.values())


class EnsembleRouter:
    """Route input to best model."""

    def __init__(self):
        self._routes: Dict[str, str] = {}  # keyword -> member_id

    def add_route(self, keyword: str, member_id: str) -> None:
        self._routes[keyword.lower()] = member_id

    def route(self, input_text: str, members: List[EnsembleMember]) -> Optional[EnsembleMember]:
        lower = input_text.lower()
        for keyword, member_id in self._routes.items():
            if keyword in lower:
                for m in members:
                    if m.member_id == member_id and m.enabled:
                        return m
        # Default to most accurate
        enabled = [m for m in members if m.enabled]
        if enabled:
            return max(enabled, key=lambda m: m.accuracy)
        return None


class EnsembleEngine:
    """Manage and run ensembles."""

    def __init__(self, ensemble_id: str, name: str):
        self.ensemble_id = ensemble_id
        self.name = name
        self._members: Dict[str, EnsembleMember] = {}
        self.voter = VotingEngine()
        self.stacker = StackingEnsemble()
        self.router = EnsembleRouter()
        self._predictions: List[EnsemblePrediction] = []

    def add_member(self, member: EnsembleMember) -> None:
        self._members[member.member_id] = member

    def remove_member(self, member_id: str) -> bool:
        return self._members.pop(member_id, None) is not None

    def predict(self, input_text: str, strategy: VoteStrategy = VoteStrategy.WEIGHTED, use_router: bool = False) -> EnsemblePrediction:
        members = list(self._members.values())
        if use_router:
            best = self.router.route(input_text, members)
            if best:
                preds = {best.member_id: best.predict(input_text)}
            else:
                preds = {}
        else:
            preds = {m.member_id: m.predict(input_text) for m in members if m.enabled}

        weights = {m.member_id: m.weight * m.accuracy for m in members}
        final, confidence = self.voter.vote(preds, weights, strategy)

        pred = EnsemblePrediction(
            prediction_id=str(uuid.uuid4())[:12],
            input_text=input_text,
            predictions=preds,
            final_output=final,
            confidence=confidence,
            strategy=strategy.name,
        )
        self._predictions.append(pred)
        return pred

    def stack_predict(self, input_text: str) -> str:
        members = [m for m in self._members.values() if m.enabled]
        return self.stacker.predict(input_text, members)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "members": len(self._members),
            "predictions": len(self._predictions),
            "avg_confidence": sum(p.confidence for p in self._predictions) / max(len(self._predictions), 1),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "ensemble_id": self.ensemble_id,
                "name": self.name,
                "members": [{"id": m.member_id, "name": m.name, "accuracy": m.accuracy} for m in self._members.values()],
                "stats": self.get_stats(),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MODEL ENSEMBLE DEMO")
    print("=" * 70)

    # 1. Create ensemble
    print("\n[1] Create Ensemble")
    ensemble = EnsembleEngine("e1", "QA Ensemble")
    ensemble.add_member(EnsembleMember("m1", "General", lambda x: f"Answer: {x[:20]}", weight=1.0, accuracy=0.7))
    ensemble.add_member(EnsembleMember("m2", "Expert", lambda x: f"Expert says: {x[:20]}", weight=1.2, accuracy=0.85))
    ensemble.add_member(EnsembleMember("m3", "Fast", lambda x: f"Quick: {x[:20]}", weight=0.8, accuracy=0.6, latency_ms=50.0))
    print(f"  Members: {len(ensemble._members)}")

    # 2. Majority vote
    print("\n[2] Majority Vote")
    # Force same prediction for majority demo
    def same_pred(x): return "Yes"
    ensemble2 = EnsembleEngine("e2", "Binary Ensemble")
    for i in range(3):
        ensemble2.add_member(EnsembleMember(f"bm{i}", f"Model{i}", same_pred, accuracy=0.7))
    ensemble2.add_member(EnsembleMember("bm3", "Model3", lambda x: "No", accuracy=0.6))
    result = ensemble2.predict("Is this true?", strategy=VoteStrategy.MAJORITY)
    print(f"  Predictions: {result.predictions}")
    print(f"  Winner: {result.final_output} (confidence={result.confidence:.2f})")

    # 3. Weighted vote
    print("\n[3] Weighted Vote")
    result = ensemble.predict("Explain AI", strategy=VoteStrategy.WEIGHTED)
    print(f"  Predictions: {result.predictions}")
    print(f"  Winner: {result.final_output[:50]}...")
    print(f"  Confidence: {result.confidence:.3f}")

    # 4. Stacking
    print("\n[4] Stacking Ensemble")
    stacked = ensemble.stack_predict("Explain AI")
    print(f"  Stacked: {stacked[:80]}...")

    # 5. Routing
    print("\n[5] Ensemble Router")
    ensemble.router.add_route("code", "m1")
    ensemble.router.add_route("math", "m2")
    for query in ["Write code for sorting", "Solve math problem", "General question"]:
        member = ensemble.router.route(query, list(ensemble._members.values()))
        print(f"  '{query[:25]}...' -> {member.name if member else 'None'}")

    # 6. Router prediction
    print("\n[6] Router-based Prediction")
    result = ensemble.predict("Code a function", use_router=True)
    print(f"  Routed prediction: {result.final_output[:50]}...")

    # 7. Stats
    print(f"\n[7] Stats")
    print(f"  {ensemble.get_stats()}")

    # 8. Export
    print("\n[8] Export")
    ensemble.export("/tmp/ensemble.json")
    print("  Exported to /tmp/ensemble.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
