#!/usr/bin/env python3
"""alignment_engine.py — Advanced Alignment by Design for MAGNATRIX-OS.

Constitution integration, temporal context, pattern-based learning, predictive alignment,
multi-agent scoring, and cascading effects.
"""

from __future__ import annotations
import time, json, os, math, statistics
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
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
    overall: float
    breakdown: Dict[str, float]
    flags: List[str]
    predicted_score: float
    temporal_penalty: float
    timestamp: float


class PatternMemory:
    """Remember violation sequences to predict future misalignment."""

    def __init__(self, max_length: int = 5):
        self.max_length = max_length
        self._sequences: List[Tuple[str, ...]] = []
        self._violation_map: Dict[Tuple[str, ...], float] = {}

    def record(self, action: Action, was_violation: bool) -> None:
        if was_violation:
            key = (action.category.value, action.actor_id)
            self._violation_map[key] = self._violation_map.get(key, 0) + 1

    def get_penalty(self, action: Action) -> float:
        key = (action.category.value, action.actor_id)
        count = self._violation_map.get(key, 0)
        return min(0.3, count * 0.05)  # escalating penalty

    def get_actor_reputation(self, actor_id: str) -> float:
        total = sum(1 for k, v in self._violation_map.items() if k[1] == actor_id)
        return max(0.0, 1.0 - total * 0.1)


class TemporalContext:
    """Sliding window context for recent actions."""

    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self._history: List[Dict[str, Any]] = []

    def add(self, action: Action, score: AlignmentScore) -> None:
        self._history.append({"action": action, "score": score, "time": time.time()})
        if len(self._history) > self.window_size:
            self._history.pop(0)

    def get_recent_flags(self, actor_id: str, window: int = 5) -> List[str]:
        recent = [h for h in self._history[-window:] if h["action"].actor_id == actor_id]
        flags = []
        for h in recent:
            flags.extend(h["score"].flags)
        return flags

    def get_recent_violations(self, actor_id: str) -> int:
        return sum(1 for h in self._history[-10:] if h["action"].actor_id == actor_id and h["score"].overall < 0.5)

    def get_cascading_penalty(self, actor_id: str) -> float:
        violations = self.get_recent_violations(actor_id)
        return min(0.4, violations * 0.08)


class AlignmentEngine:
    """Advanced alignment with constitution, temporal context, pattern learning, prediction."""

    VALUES = ["safety", "privacy", "fairness", "autonomy", "truth"]

    def __init__(self, constitution_store: Any = None, threshold: float = 0.7):
        self.constitution = constitution_store
        self.threshold = threshold
        self._scores: List[AlignmentScore] = []
        self._interventions: List[Dict[str, Any]] = []
        self._learning_weights: Dict[str, float] = {v: 1.0 for v in self.VALUES}
        self._action_history: List[Action] = []
        self._rules: Dict[str, Callable[[Action], float]] = self._init_rules()
        self._pattern_memory = PatternMemory()
        self._temporal_context = TemporalContext()
        self._peer_scores: Dict[str, List[float]] = {}  # multi-agent peer scores

    def _init_rules(self) -> Dict[str, Callable[[Action], float]]:
        base = {
            "safety": lambda a: 0.3 if a.category == ActionCategory.SELF_MODIFICATION and not a.metadata.get("sandboxed") else 1.0,
            "privacy": lambda a: 0.2 if a.category == ActionCategory.DATA_ACCESS and a.metadata.get("sensitive") and not a.metadata.get("consent") else 1.0,
            "fairness": lambda a: 0.5 if a.metadata.get("bias_detected") else 1.0,
            "autonomy": lambda a: 0.4 if a.category == ActionCategory.EXECUTION and a.metadata.get("overrides_user") else 1.0,
            "truth": lambda a: 0.3 if a.metadata.get("unverified_claim") else 1.0,
        }
        # If constitution available, enhance rules
        if self.constitution:
            articles = self.constitution.list_all() if hasattr(self.constitution, "list_all") else []
            for article in articles:
                if article.id == "A002" and "Privacy" in article.title:  # enhance privacy
                    base["privacy"] = lambda a: 0.1 if a.category == ActionCategory.DATA_ACCESS and a.metadata.get("sensitive") and not a.metadata.get("consent") else 1.0
        return base

    def score_action(self, action: Action) -> AlignmentScore:
        breakdown = {}
        flags = []
        for value in self.VALUES:
            weight = self._learning_weights[value]
            raw = self._rules[value](action)
            # Apply pattern-based penalty for repeat offenders
            pattern_penalty = self._pattern_memory.get_penalty(action)
            # Apply temporal cascading penalty
            temporal_penalty = self._temporal_context.get_cascading_penalty(action.actor_id)
            score = max(0.0, raw * weight - pattern_penalty - temporal_penalty)
            breakdown[value] = score
            if score < 0.5:
                flags.append(f"LOW_{value.upper()}: {action.action_id}")

        overall = sum(breakdown.values()) / len(breakdown)
        # Predictive score: simulate what score would be if action proceeds
        predicted = self._predict_outcome(action, breakdown)
        score = AlignmentScore(
            action_id=action.action_id, overall=overall, breakdown=breakdown,
            flags=flags, predicted_score=predicted, temporal_penalty=temporal_penalty,
            timestamp=time.time(),
        )
        self._scores.append(score)
        self._action_history.append(action)
        self._temporal_context.add(action, score)
        self._pattern_memory.record(action, overall < 0.5)
        return score

    def _predict_outcome(self, action: Action, current_breakdown: Dict[str, float]) -> float:
        """Predict score if this action triggers follow-up actions."""
        if action.category == ActionCategory.SELF_MODIFICATION and not action.metadata.get("sandboxed"):
            return 0.2  # High risk of cascading issues
        if action.metadata.get("overrides_user"):
            return 0.3
        return statistics.mean(current_breakdown.values())

    def should_intervene(self, score: AlignmentScore) -> bool:
        return score.overall < self.threshold or score.predicted_score < 0.4 or len(score.flags) > 2

    def intervene(self, action: Action, score: AlignmentScore) -> Dict[str, Any]:
        intervention = {
            "action_id": action.action_id, "decision": "BLOCKED",
            "reason": f"Score {score.overall:.3f} below threshold {self.threshold}, predicted {score.predicted_score:.3f}",
            "flags": score.flags, "timestamp": time.time(),
            "explanation": self._explain(action, score),
            "recommendation": self._generate_recommendation(action, score),
        }
        if score.overall >= 0.4 and score.predicted_score >= 0.4:
            intervention["decision"] = "WARN_AND_REQUIRE_CONFIRMATION"
        elif score.overall >= 0.3:
            intervention["decision"] = "WARN_AND_LOG"
        self._interventions.append(intervention)
        return intervention

    def _explain(self, action: Action, score: AlignmentScore) -> str:
        parts = [f"Action {action.action_id} ({action.category.value}) by {action.actor_id}: score={score.overall:.3f}, predicted={score.predicted_score:.3f}"]
        for v, s in score.breakdown.items():
            if s < 0.5:
                parts.append(f"  {v}: {s:.3f} — {self._value_explanation(v, action)}")
        if score.temporal_penalty > 0:
            parts.append(f"  temporal_penalty: {score.temporal_penalty:.3f} (repeat actor history)")
        return "; ".join(parts)

    def _value_explanation(self, value: str, action: Action) -> str:
        explanations = {
            "safety": "self-modification without sandbox detected",
            "privacy": "sensitive data access without consent",
            "fairness": "bias detected in decision",
            "autonomy": "user override detected",
            "truth": "unverified claim in output",
        }
        return explanations.get(value, "value violation")

    def _generate_recommendation(self, action: Action, score: AlignmentScore) -> str:
        if score.predicted_score < 0.3:
            return "Immediate block required. Escalate to human operator."
        if action.category == ActionCategory.SELF_MODIFICATION:
            return "Require sandboxed execution with approval."
        if action.category == ActionCategory.DATA_ACCESS:
            return "Request explicit user consent before proceeding."
        return "Review action details and approve with logging."

    def process(self, action: Action) -> Dict[str, Any]:
        score = self.score_action(action)
        if self.should_intervene(score):
            return self.intervene(action, score)
        return {
            "action_id": action.action_id, "decision": "ALLOWED",
            "score": score.overall, "predicted": score.predicted_score,
            "timestamp": time.time(),
        }

    def multi_agent_review(self, action: Action, peer_scores: Dict[str, float]) -> Dict[str, Any]:
        """Peer review from multiple agents."""
        self._peer_scores[action.action_id] = list(peer_scores.values())
        avg_peer = statistics.mean(peer_scores.values()) if peer_scores else 1.0
        my_score = self.score_action(action)
        consensus = (my_score.overall + avg_peer) / 2
        return {
            "action_id": action.action_id, "my_score": my_score.overall,
            "peer_avg": avg_peer, "consensus": consensus,
            "decision": "ALLOWED" if consensus >= self.threshold else "PEER_REVIEW_BLOCKED",
            "dissenters": [k for k, v in peer_scores.items() if v < self.threshold],
        }

    def learn(self, feedback: Dict[str, Any]) -> None:
        for value in self.VALUES:
            delta = feedback.get(value, 0)
            if delta != 0:
                self._learning_weights[value] += delta * 0.05
                self._learning_weights[value] = max(0.1, min(2.0, self._learning_weights[value]))
        # Also learn from pattern memory
        actor_id = feedback.get("actor_id", "")
        if actor_id:
            self._pattern_memory.record(
                Action("learn", ActionCategory.EXECUTION, "", time.time(), actor_id),
                feedback.get("was_violation", False),
            )

    def get_stats(self) -> Dict[str, Any]:
        if not self._scores:
            return {}
        scores = [s.overall for s in self._scores]
        predictions = [s.predicted_score for s in self._scores]
        return {
            "total_actions": len(self._scores), "avg_score": sum(scores) / len(scores),
            "min_score": min(scores), "interventions": len(self._interventions),
            "weights": self._learning_weights, "avg_prediction_accuracy": 1.0 - abs(statistics.mean(predictions) - statistics.mean(scores)),
        }

    def audit(self) -> List[Dict[str, Any]]:
        return self._interventions


if __name__ == "__main__":
    engine = AlignmentEngine()
    actions = [
        Action("A1", ActionCategory.DATA_ACCESS, "Read user file", time.time(), "agent_1", metadata={"sensitive": True, "consent": True}),
        Action("A2", ActionCategory.DATA_ACCESS, "Read without consent", time.time(), "agent_1", metadata={"sensitive": True, "consent": False}),
        Action("A3", ActionCategory.EXECUTION, "Run command", time.time(), "agent_1", metadata={"overrides_user": False}),
        Action("A4", ActionCategory.SELF_MODIFICATION, "Patch own code", time.time(), "agent_1", metadata={"sandboxed": True}),
        Action("A5", ActionCategory.SELF_MODIFICATION, "Patch unsandboxed", time.time(), "agent_1", metadata={"sandboxed": False}),
        Action("A6", ActionCategory.SELF_MODIFICATION, "Another unsandboxed", time.time(), "agent_1", metadata={"sandboxed": False}),
    ]
    for a in actions:
        result = engine.process(a)
        print(f"{a.action_id} ({a.category.value}): {result['decision']} score={result.get('score', 'N/A')} pred={result.get('predicted', 'N/A')}")
        if result['decision'] == 'BLOCKED':
            print(f"  Reason: {result['reason']}")
            print(f"  Rec: {result.get('recommendation', '')}")
    # Multi-agent review
    peer_scores = {"agent_2": 0.9, "agent_3": 0.8, "agent_4": 0.3}
    review = engine.multi_agent_review(actions[4], peer_scores)
    print(f"Peer review: {review}")
    print(f"Stats: {engine.get_stats()}")
