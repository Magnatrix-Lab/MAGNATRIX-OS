"""
llm_load_shedder_native.py
MAGNATRIX-OS Load Shedder Engine
Native Python, stdlib only.
Provides load shedding with priority-based dropping, rate control, backpressure, and graceful degradation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class PriorityLevel(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class LoadSheddingAction(Enum):
    ADMIT = "admit"
    DELAY = "delay"
    DROP = "drop"
    REDIRECT = "redirect"


@dataclass
class RequestProfile:
    request_id: str
    priority: PriorityLevel
    estimated_cost: float
    timestamp: float
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class LoadShedderEngine:
    """Load shedding with priority-based admission control."""

    def __init__(self, max_concurrent: int = 100, max_queue: int = 50,
                 latency_threshold_ms: float = 1000.0) -> None:
        self.max_concurrent = max_concurrent
        self.max_queue = max_queue
        self.latency_threshold_ms = latency_threshold_ms
        self._active = 0
        self._queued = 0
        self._dropped = 0
        self._admitted = 0
        self._current_load = 0.0
        self._shedding_enabled = False
        self._priority_threshold = PriorityLevel.BACKGROUND

    def estimate_load(self) -> float:
        return self._current_load

    def set_load(self, active_requests: int, queue_depth: int, avg_latency_ms: float) -> None:
        self._active = active_requests
        self._queued = queue_depth
        load_factor = (active_requests / self.max_concurrent) + (queue_depth / self.max_queue)
        self._current_load = min(1.0, load_factor + (avg_latency_ms / self.latency_threshold_ms))
        self._shedding_enabled = self._current_load > 0.8
        if self._current_load > 0.9:
            self._priority_threshold = PriorityLevel.HIGH
        elif self._current_load > 0.7:
            self._priority_threshold = PriorityLevel.NORMAL
        else:
            self._priority_threshold = PriorityLevel.BACKGROUND

    def admit(self, request: RequestProfile) -> LoadSheddingAction:
        if request.priority.value < self._priority_threshold.value:
            self._admitted += 1
            return LoadSheddingAction.ADMIT
        if self._shedding_enabled:
            if self._queued >= self.max_queue:
                self._dropped += 1
                return LoadSheddingAction.DROP
            if request.priority.value <= PriorityLevel.NORMAL.value:
                return LoadSheddingAction.DELAY
            self._dropped += 1
            return LoadSheddingAction.DROP
        self._admitted += 1
        return LoadSheddingAction.ADMIT

    def get_stats(self) -> Dict[str, Any]:
        total = self._admitted + self._dropped
        return {
            "active": self._active, "queued": self._queued,
            "current_load": round(self._current_load, 3),
            "shedding_enabled": self._shedding_enabled,
            "priority_threshold": self._priority_threshold.value,
            "admitted": self._admitted, "dropped": self._dropped,
            "drop_rate": self._dropped / total if total > 0 else 0.0,
        }

    def reset(self) -> None:
        self._active = 0
        self._queued = 0
        self._dropped = 0
        self._admitted = 0
        self._current_load = 0.0


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Load Shedder Engine")
    print("=" * 60)

    engine = LoadShedderEngine(max_concurrent=100, max_queue=20)

    print("\n--- Normal load ---")
    engine.set_load(active_requests=40, queue_depth=5, avg_latency_ms=200)
    for priority in PriorityLevel:
        req = RequestProfile("r1", priority, 1.0, time.time())
        action = engine.admit(req)
        print(f"  {priority.value}: {action.value}")

    print("\n--- High load ---")
    engine.reset()
    engine.set_load(active_requests=90, queue_depth=18, avg_latency_ms=800)
    for priority in PriorityLevel:
        req = RequestProfile("r2", priority, 1.0, time.time())
        action = engine.admit(req)
        print(f"  {priority.value}: {action.value}")

    print("\n--- Overload ---")
    engine.reset()
    engine.set_load(active_requests=120, queue_depth=25, avg_latency_ms=1500)
    for priority in PriorityLevel:
        req = RequestProfile("r3", priority, 1.0, time.time())
        action = engine.admit(req)
        print(f"  {priority.value}: {action.value}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nLoad Shedder test complete.")


if __name__ == "__main__":
    run()
