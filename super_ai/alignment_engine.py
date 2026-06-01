#!/usr/bin/env python3
"""alignment_engine.py — Alignment by Design for MAGNATRIX-OS.

Real-time behavior scoring, deviation detection, intervention, and learning loop.
Wires dengan constitution.py untuk value extraction.
"""

from __future__ import annotations
import time, json, os, math
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ActionCategory(Enum):
    DATA_ACCESS = "data_access"
    EXECUTION = "execution"
    COMMUNICATION = "communication"
    RESOURCE_ALLOC = "resource_alloc"
    SELF_MODIFICATION = "self_modification"


@dataclass
class Action:
    action_id: str
    category: ActionCategory
    description: str
    timestamp: float
    actor_id: str
    target: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlignmentScore:
    action_id: str
    overall: float  # 0.0 - 1.0
    breakdown: Dict[str, float]
    flags: List[str]
    timestamp: float


class AlignmentEngine:
    """Monitor actions, score against constitution values, intervene if needed."""

    VALUES = ["safety", "privacy", "fairness", "autonomy", "truth"]

    def __init__(self, constitution_store: Any = None, threshold: float = 0.7):
        self.constitution = constitution_store
        self.threshold = threshold
        self._scores: List[AlignmentScore] = []
        self._interventions: List[Dict[str, Any]] = []
        self._learning_weights: Dict[str, float] = {v: 1.0 for v in self.VALUES}
        self._action_history: List[Action] = []
        self._rules: Dict[str, Callable[[Action], float]] = self._init_rules()

    def _init_rules(self) -> Dict[str, Callable[[Action], float]]:
        return {
            "safety": lambda a: 0.3 if a.category == ActionCategory.SELF_MODIFICATION and not a.metadata.get("sandboxed") else 1.0,
            "privacy": lambda a: 0.2 if a.category == ActionCategory.DATA_ACCESS and a.metadata.get("sensitive") and not a.metadata.get("consent") else 1.0,
            "fairness": lambda a: 0.5 if a.metadata.get("bias_detected") else 1.0,
            "autonomy": lambda a: 0.4 if a.category == ActionCategory.EXECUTION and a.metadata.get("overrides_user") else 1.0,
            "truth": lambda a: 0.3 if a.metadata.get("unverified_claim") else 1.0,
        }

    def score_action(self, action: Action) -> AlignmentScore:
        breakdown = {}
        flags = []
        for value in self.VALUES:
            weight = self._learning_weights[value]
            raw = self._rules[value](action)
            score = raw * weight
            breakdown[value] = score
            if score < 0.5:
                flags.append(f"LOW_{value.upper()}: {action.action_id}")
        overall = sum(breakdown.values()) / len(breakdown)
        score = AlignmentScore(
            action_id=action.action_id,
            overall=overall,
            breakdown=breakdown,
            flags=flags,
            timestamp=time.time(),
        )
        self._scores.append(score)
        self._action_history.append(action)
        return score

    def should_intervene(self, score: AlignmentScore) -> bool:
        return score.overall < self.threshold or len(score.flags) > 2

    def intervene(self, action: Action, score: AlignmentScore) -> Dict[str, Any]:
        intervention = {
            "action_id": action.action_id,
            "decision": "BLOCKED",
            "reason": f"Alignment score {score.overall:.3f} below threshold {self.threshold}",
            "flags": score.flags,
            "timestamp": time.time(),
            "explanation": self._explain(action, score),
        }
        if score.overall >= 0.4:
            intervention["decision"] = "WARN_AND_LOG"
        self._interventions.append(intervention)
        return intervention

    def _explain(self, action: Action, score: AlignmentScore) -> str:
        parts = [f"Action {action.action_id} ({action.category.value}) scored {score.overall:.3f}"]
        for v, s in score.breakdown.items():
            if s < 0.5:
                parts.append(f"  {v}: {s:.3f} — needs attention")
        return "; ".join(parts)

    def process(self, action: Action) -> Dict[str, Any]:
        score = self.score_action(action)
        if self.should_intervene(score):
            return self.intervene(action, score)
        return {
            "action_id": action.action_id,
            "decision": "ALLOWED",
            "score": score.overall,
            "timestamp": time.time(),
        }

    def learn(self, feedback: Dict[str, Any]) -> None:
        """Adjust weights from feedback: {value: +1/-1, action_id: str}."""
        for value in self.VALUES:
            delta = feedback.get(value, 0)
            if delta != 0:
                self._learning_weights[value] += delta * 0.05
                self._learning_weights[value] = max(0.1, min(2.0, self._learning_weights[value]))

    def get_stats(self) -> Dict[str, Any]:
        if not self._scores:
            return {}
        scores = [s.overall for s in self._scores]
        return {
            "total_actions": len(self._scores),
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "interventions": len(self._interventions),
            "weights": self._learning_weights,
        }

    def audit(self) -> List[Dict[str, Any]]:
        return self._interventions


if __name__ == "__main__":
    engine = AlignmentEngine()
    actions = [
        Action("A1", ActionCategory.DATA_ACCESS, "Read user file", time.time(), "agent_1", metadata={"sensitive": True, "consent": True}),
        Action("A2", ActionCategory.DATA_ACCESS, "Read user file without consent", time.time(), "agent_1", metadata={"sensitive": True, "consent": False}),
        Action("A3", ActionCategory.EXECUTION, "Run command", time.time(), "agent_1", metadata={"overrides_user": False}),
        Action("A4", ActionCategory.SELF_MODIFICATION, "Patch own code", time.time(), "agent_1", metadata={"sandboxed": True}),
        Action("A5", ActionCategory.SELF_MODIFICATION, "Patch own code unsandboxed", time.time(), "agent_1", metadata={"sandboxed": False}),
    ]
    for a in actions:
        result = engine.process(a)
        print(f"{a.action_id} ({a.category.value}): {result['decision']} score={result.get('score', 'N/A')}")
        if result['decision'] == 'BLOCKED':
            print(f"  Reason: {result['reason']}")
    print(f"Stats: {engine.get_stats()}")
