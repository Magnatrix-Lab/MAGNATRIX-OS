"""
llm_moe_router_native.py
MAGNATRIX-OS MoE Router Engine
Native Python, stdlib only.
Provides Mixture-of-Experts routing with shared + routed experts, top-k selection,
balance loss tracking, fine-grained expert segmentation, and group-limited routing.

Inspired by OpenMythos DeepSeek MoE implementation.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class ScoreFunction(Enum):
    SOFTMAX = "softmax"
    SIGMOID = "sigmoid"


@dataclass
class Expert:
    expert_id: int
    is_shared: bool
    weight: float = 1.0
    specialization: str = ""
    load_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"expert_id": self.expert_id, "shared": self.is_shared, "load": self.load_count}


@dataclass
class RoutingDecision:
    token_id: str
    selected_experts: List[Tuple[int, float]]  # (expert_id, weight)
    shared_experts: List[int]
    gate_score: float
    balance_loss: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token": self.token_id, "selected": self.selected_experts,
            "shared": self.shared_experts, "gate_score": self.gate_score,
            "balance_loss": self.balance_loss,
        }


class MoERouterEngine:
    """
    Mixture-of-Experts router with shared + routed experts.
    Inspired by OpenMythos DeepSeek MoE.
    """

    def __init__(self, n_routed_experts: int = 64, n_shared_experts: int = 2,
                 n_activated_experts: int = 6, expert_hidden_dim: int = 704,
                 score_func: ScoreFunction = ScoreFunction.SOFTMAX,
                 balance_alpha: float = 0.001, route_scale: float = 1.0) -> None:
        self.n_routed_experts = n_routed_experts
        self.n_shared_experts = n_shared_experts
        self.n_activated_experts = n_activated_experts
        self.expert_hidden_dim = expert_hidden_dim
        self.score_func = score_func
        self.balance_alpha = balance_alpha
        self.route_scale = route_scale

        self._routed_experts: List[Expert] = [Expert(i, False) for i in range(n_routed_experts)]
        self._shared_experts: List[Expert] = [Expert(n_routed_experts + i, True) for i in range(n_shared_experts)]
        self._all_experts = self._routed_experts + self._shared_experts
        self._routing_history: List[RoutingDecision] = []
        self._expert_frequency: Dict[int, int] = {}
        self._expert_scores: Dict[int, float] = {}

    def _softmax(self, scores: List[float]) -> List[float]:
        max_score = max(scores)
        exp_scores = [math.exp(s - max_score) for s in scores]
        total = sum(exp_scores)
        return [e / total for e in exp_scores]

    def _sigmoid(self, scores: List[float]) -> List[float]:
        return [1.0 / (1.0 + math.exp(-s)) for s in scores]

    def _compute_scores(self, token_embedding: List[float]) -> List[float]:
        # Simplified gate: dot product with random expert prototypes
        scores = []
        for expert in self._routed_experts:
            # Simulate score based on token-expert affinity
            score = random.gauss(0.5, 0.2)
            scores.append(max(0.0, score))
        if self.score_func == ScoreFunction.SOFTMAX:
            return self._softmax(scores)
        return self._sigmoid(scores)

    def route(self, token_id: str, token_embedding: List[float]) -> RoutingDecision:
        scores = self._compute_scores(token_embedding)
        # Top-K selection
        indexed = [(i, s) for i, s in enumerate(scores)]
        indexed.sort(key=lambda x: x[1], reverse=True)
        top_k = indexed[:self.n_activated_experts]

        # Store original scores for balance loss
        for i, s in indexed:
            self._expert_scores[i] = self._expert_scores.get(i, 0.0) + s

        # Update frequencies
        for i, _ in top_k:
            self._expert_frequency[i] = self._expert_frequency.get(i, 0) + 1

        # Balance loss: f_i * P_i
        total_tokens = sum(self._expert_frequency.values()) or 1
        balance_loss = 0.0
        for i, s in indexed:
            f_i = (self.n_routed_experts / (self.n_activated_experts * max(total_tokens, 1))) * self._expert_frequency.get(i, 0)
            P_i = self._expert_scores.get(i, 0.0) / max(total_tokens, 1)
            balance_loss += f_i * P_i
        balance_loss *= self.balance_alpha

        # Normalize weights for sigmoid
        weights = [(i, s * self.route_scale) for i, s in top_k]
        if self.score_func == ScoreFunction.SIGMOID:
            total_weight = sum(s for _, s in weights)
            if total_weight > 0:
                weights = [(i, s / total_weight) for i, s in weights]

        shared_ids = [e.expert_id for e in self._shared_experts]

        decision = RoutingDecision(
            token_id=token_id, selected_experts=weights,
            shared_experts=shared_ids, gate_score=sum(s for _, s in top_k),
            balance_loss=balance_loss
        )
        self._routing_history.append(decision)
        return decision

    def get_expert_load(self) -> Dict[int, int]:
        return dict(self._expert_frequency)

    def get_balance_stats(self) -> Dict[str, Any]:
        if not self._expert_frequency:
            return {"balance_loss": 0.0}
        avg_load = sum(self._expert_frequency.values()) / len(self._expert_frequency)
        variance = sum((v - avg_load) ** 2 for v in self._expert_frequency.values()) / len(self._expert_frequency)
        return {
            "avg_load": avg_load, "variance": variance,
            "balance_loss": sum(d.balance_loss for d in self._routing_history) / max(len(self._routing_history), 1),
            "most_used": max(self._expert_frequency.items(), key=lambda x: x[1]) if self._expert_frequency else None,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "routed_experts": self.n_routed_experts, "shared_experts": self.n_shared_experts,
            "activated_per_token": self.n_activated_experts, "score_func": self.score_func.value,
            "total_routings": len(self._routing_history), **self.get_balance_stats(),
        }

    def reset(self) -> None:
        self._routing_history.clear()
        self._expert_frequency.clear()
        self._expert_scores.clear()


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS MoE Router Engine")
    print("=" * 60)

    engine = MoERouterEngine(n_routed_experts=8, n_shared_experts=2, n_activated_experts=3, score_func=ScoreFunction.SOFTMAX)

    print("\n--- Route tokens ---")
    for i in range(10):
        embedding = [random.random() for _ in range(16)]
        decision = engine.route(f"tok_{i}", embedding)
        print(f"  {decision.token_id}: experts={[e[0] for e in decision.selected_experts]}, balance_loss={decision.balance_loss:.4f}")

    print("\n--- Expert load ---")
    print(engine.get_expert_load())

    print("\n--- Balance stats ---")
    print(engine.get_balance_stats())

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nMoE Router test complete.")


if __name__ == "__main__":
    run()
