"""
llm_act_halting_native.py
MAGNATRIX-OS ACT Halting Engine
Native Python, stdlib only.
Provides Adaptive Computation Time halting with cumulative probability gates,
thinking depth control, and per-iteration confidence scoring.

Inspired by OpenMythos ACT halting mechanism in Recurrent-Depth Transformers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class HaltingStatus(Enum):
    THINKING = "thinking"
    READY = "ready"
    HALTED = "halted"
    TIMEOUT = "timeout"


@dataclass
class HaltingState:
    iteration: int = 0
    cumulative_probability: float = 0.0
    residual_probability: float = 1.0
    confidence: float = 0.0
    status: HaltingStatus = HaltingStatus.THINKING
    ponder_cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration, "cum_prob": self.cumulative_probability,
            "residual": self.residual_probability, "confidence": self.confidence,
            "status": self.status.value, "ponder_cost": self.ponder_cost,
        }


class ACTHaltingEngine:
    """
    Adaptive Computation Time halting controller.
    Inspired by OpenMythos ACT mechanism.
    """

    def __init__(self, threshold: float = 0.99, max_iterations: int = 16,
                 ponder_cost_weight: float = 0.01) -> None:
        self.threshold = threshold
        self.max_iterations = max_iterations
        self.ponder_cost_weight = ponder_cost_weight
        self._state = HaltingState()
        self._history: List[HaltingState] = []
        self._halting_fn: Optional[Callable[[Any, int], float]] = None

    def set_halting_function(self, fn: Callable[[Any, int], float]) -> None:
        self._halting_fn = fn

    def default_halting(self, state: Any, iteration: int) -> float:
        # Default: sigmoid-based confidence that increases with iteration
        base = 0.1 * iteration
        noise = 0.05 * (hash(str(state)) % 10) / 10
        return min(1.0, base + noise + 0.2)

    def step(self, state: Any) -> Tuple[bool, HaltingState]:
        self._state.iteration += 1

        if self._halting_fn:
            halt_prob = self._halting_fn(state, self._state.iteration)
        else:
            halt_prob = self.default_halting(state, self._state.iteration)

        halt_prob = max(0.0, min(1.0, halt_prob))

        # Update probabilities
        self._state.cumulative_probability += self._state.residual_probability * halt_prob
        self._state.residual_probability *= (1.0 - halt_prob)
        self._state.confidence = halt_prob
        self._state.ponder_cost += self.ponder_cost_weight * self._state.residual_probability

        # Check halting conditions
        if self._state.cumulative_probability >= self.threshold:
            self._state.status = HaltingStatus.HALTED
            return True, self._state

        if self._state.iteration >= self.max_iterations:
            self._state.status = HaltingStatus.TIMEOUT
            return True, self._state

        if self._state.residual_probability < 0.01:
            self._state.status = HaltingStatus.READY
            return True, self._state

        self._state.status = HaltingStatus.THINKING
        self._history.append(HaltingState(
            iteration=self._state.iteration,
            cumulative_probability=self._state.cumulative_probability,
            residual_probability=self._state.residual_probability,
            confidence=self._state.confidence,
            status=self._state.status,
            ponder_cost=self._state.ponder_cost,
        ))
        return False, self._state

    def run(self, initial_state: Any, update_fn: Callable[[Any, int], Any]) -> Tuple[Any, HaltingState]:
        self.reset()
        state = initial_state
        while True:
            should_halt, halting_state = self.step(state)
            if should_halt:
                return state, halting_state
            state = update_fn(state, self._state.iteration)

    def reset(self) -> None:
        self._state = HaltingState()
        self._history.clear()

    def get_stats(self) -> Dict[str, Any]:
        avg_confidence = sum(h.confidence for h in self._history) / max(len(self._history), 1) if self._history else 0.0
        return {
            "threshold": self.threshold, "max_iterations": self.max_iterations,
            "final_iteration": self._state.iteration, "final_cum_prob": self._state.cumulative_probability,
            "final_residual": self._state.residual_probability, "ponder_cost": self._state.ponder_cost,
            "avg_confidence": round(avg_confidence, 4), "status": self._state.status.value,
            "history_length": len(self._history),
        }

    def get_history(self) -> List[Dict[str, Any]]:
        return [h.to_dict() for h in self._history]


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS ACT Halting Engine")
    print("=" * 60)

    engine = ACTHaltingEngine(threshold=0.95, max_iterations=10, ponder_cost_weight=0.01)

    def update_fn(state: str, iteration: int) -> str:
        return f"{state} [think_{iteration}]"

    def halting_fn(state: str, iteration: int) -> float:
        # Fast convergence: halts around iteration 5
        return 0.15 * iteration + 0.1

    engine.set_halting_function(halting_fn)

    print("\n--- Run ---")
    final_state, final_halting = engine.run("Start", update_fn)
    print(f"  Final state: {final_state}")
    print(f"  Iterations: {final_halting.iteration}")
    print(f"  Cumulative prob: {final_halting.cumulative_probability:.4f}")
    print(f"  Status: {final_halting.status.value}")

    print("\n--- History ---")
    for h in engine.get_history():
        print(f"  Iter {h['iteration']}: conf={h['confidence']:.3f}, cum={h['cum_prob']:.3f}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nACT Halting test complete.")


if __name__ == "__main__":
    run()
