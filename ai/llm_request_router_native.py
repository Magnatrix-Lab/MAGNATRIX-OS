"""
llm_request_router_native.py
MAGNATRIX-OS Request Router Engine
Native Python, stdlib only.
Provides intelligent request routing with model selection, fallback chains, A/B testing, and latency-based routing.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class RoutingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LATENCY_BASED = "latency_based"
    WEIGHTED = "weighted"
    FALLBACK = "fallback"
    AB_TEST = "ab_test"
    CUSTOM = "custom"


@dataclass
class RouteTarget:
    model_id: str
    weight: float = 1.0
    latency_ms: float = 0.0
    error_rate: float = 0.0
    capacity: float = 1.0
    current_load: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"model_id": self.model_id, "weight": self.weight, "latency_ms": self.latency_ms, "load": self.current_load}

    @property
    def score(self) -> float:
        # Lower is better
        latency_score = self.latency_ms / 1000.0
        error_score = self.error_rate * 10
        load_score = self.current_load / max(self.capacity, 0.001)
        return latency_score + error_score + load_score


class RequestRouterEngine:
    """Intelligent request routing with multiple strategies."""

    def __init__(self) -> None:
        self._targets: Dict[str, List[RouteTarget]] = {}
        self._strategies: Dict[str, RoutingStrategy] = {}
        self._custom_routers: Dict[str, Callable] = {}
        self._round_robin_idx: Dict[str, int] = {}
        self._ab_assignments: Dict[str, str] = {}  # request_id -> model_id

    def register_route(self, route_name: str, targets: List[RouteTarget], strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN) -> None:
        self._targets[route_name] = targets
        self._strategies[route_name] = strategy
        self._round_robin_idx[route_name] = 0

    def set_custom_router(self, route_name: str, router: Callable) -> None:
        self._custom_routers[route_name] = router

    def route(self, route_name: str, request_id: str = "", context: Optional[Dict[str, Any]] = None) -> Optional[RouteTarget]:
        targets = self._targets.get(route_name, [])
        if not targets:
            return None
        strategy = self._strategies.get(route_name, RoutingStrategy.ROUND_ROBIN)

        if strategy == RoutingStrategy.ROUND_ROBIN:
            idx = self._round_robin_idx.get(route_name, 0) % len(targets)
            self._round_robin_idx[route_name] = idx + 1
            return targets[idx]

        elif strategy == RoutingStrategy.LATENCY_BASED:
            return min(targets, key=lambda t: t.score)

        elif strategy == RoutingStrategy.WEIGHTED:
            total = sum(t.weight for t in targets)
            pick = random.uniform(0, total)
            cumulative = 0.0
            for t in targets:
                cumulative += t.weight
                if pick <= cumulative:
                    return t
            return targets[-1]

        elif strategy == RoutingStrategy.FALLBACK:
            for t in targets:
                if t.error_rate < 0.5 and t.current_load < t.capacity:
                    return t
            return targets[0] if targets else None

        elif strategy == RoutingStrategy.AB_TEST:
            if request_id in self._ab_assignments:
                model_id = self._ab_assignments[request_id]
                for t in targets:
                    if t.model_id == model_id:
                        return t
            # Random assignment
            target = random.choice(targets)
            self._ab_assignments[request_id] = target.model_id
            return target

        elif strategy == RoutingStrategy.CUSTOM and route_name in self._custom_routers:
            return self._custom_routers[route_name](targets, context)

        return targets[0]

    def report_latency(self, route_name: str, model_id: str, latency_ms: float) -> None:
        for t in self._targets.get(route_name, []):
            if t.model_id == model_id:
                t.latency_ms = (t.latency_ms * 0.7) + (latency_ms * 0.3)

    def report_error(self, route_name: str, model_id: str) -> None:
        for t in self._targets.get(route_name, []):
            if t.model_id == model_id:
                t.error_rate = min(1.0, t.error_rate + 0.1)

    def report_success(self, route_name: str, model_id: str) -> None:
        for t in self._targets.get(route_name, []):
            if t.model_id == model_id:
                t.error_rate = max(0.0, t.error_rate - 0.05)

    def get_stats(self, route_name: Optional[str] = None) -> Dict[str, Any]:
        if route_name:
            targets = self._targets.get(route_name, [])
            return {
                "route": route_name, "targets": len(targets),
                "avg_latency": sum(t.latency_ms for t in targets) / len(targets) if targets else 0,
                "avg_error_rate": sum(t.error_rate for t in targets) / len(targets) if targets else 0,
            }
        return {k: self.get_stats(k) for k in self._targets.keys()}


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Request Router Engine")
    print("=" * 60)

    engine = RequestRouterEngine()

    targets = [
        RouteTarget("gpt-4o", weight=1.0, latency_ms=100, error_rate=0.01),
        RouteTarget("claude-3", weight=1.5, latency_ms=150, error_rate=0.02),
        RouteTarget("local-llm", weight=0.5, latency_ms=500, error_rate=0.05),
    ]

    print("\n--- Round Robin ---")
    engine.register_route("default", targets, RoutingStrategy.ROUND_ROBIN)
    for i in range(5):
        target = engine.route("default")
        print(f"  Request {i+1}: -> {target.model_id}")

    print("\n--- Latency Based ---")
    engine.register_route("fast", targets, RoutingStrategy.LATENCY_BASED)
    for i in range(3):
        target = engine.route("fast")
        print(f"  Request {i+1}: -> {target.model_id} (score={target.score:.3f})")

    print("\n--- A/B Test ---")
    engine.register_route("experiment", targets[:2], RoutingStrategy.AB_TEST)
    assignments: Dict[str, int] = {}
    for i in range(10):
        target = engine.route("experiment", request_id=f"req_{i}")
        assignments[target.model_id] = assignments.get(target.model_id, 0) + 1
    print(f"  Assignments: {assignments}")

    print("\n--- Fallback ---")
    engine.register_route("reliable", targets, RoutingStrategy.FALLBACK)
    # Simulate failures on gpt-4o
    engine.report_error("reliable", "gpt-4o")
    engine.report_error("reliable", "gpt-4o")
    target = engine.route("reliable")
    print(f"  After errors: -> {target.model_id}")

    print("\nRequest Router test complete.")


if __name__ == "__main__":
    run()
