"""Load Balancer — Multi-model routing dengan health checks, weights, dan strategies.

Modul ini menyediakan:
- ModelNode dengan health, latency, dan capacity tracking
- LoadBalancer dengan round-robin, weighted, least-latency, dan capacity-based routing
- HealthChecker dengan periodic checks dan failure detection
- Circuit breaker untuk failing nodes
- Request routing dengan fallback
"""

from __future__ import annotations

import json
import time
import uuid
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class NodeStatus(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    DOWN = auto()


class RoutingStrategy(Enum):
    ROUND_ROBIN = auto()
    WEIGHTED = auto()
    LEAST_LATENCY = auto()
    CAPACITY_BASED = auto()
    RANDOM = auto()


class CircuitState(Enum):
    CLOSED = auto()  # Normal operation
    OPEN = auto()    # Failing, rejecting requests
    HALF_OPEN = auto()  # Testing if recovered


@dataclass
class ModelNode:
    """Single model node dalam pool."""
    node_id: str
    name: str
    endpoint: str = ""
    weight: float = 1.0
    max_capacity: int = 100  # concurrent requests
    current_load: int = 0
    avg_latency_ms: float = 100.0
    status: NodeStatus = NodeStatus.HEALTHY
    last_check: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    circuit_state: CircuitState = CircuitState.CLOSED
    circuit_failures: int = 0
    circuit_last_failure: float = 0.0

    def available_capacity(self) -> int:
        return max(0, self.max_capacity - self.current_load)

    def is_available(self) -> bool:
        return self.status != NodeStatus.DOWN and self.circuit_state != CircuitState.OPEN and self.available_capacity() > 0

    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total


@dataclass
class RoutingResult:
    """Hasil routing decision."""
    node_id: str
    strategy: RoutingStrategy
    estimated_latency: float
    fallback_used: bool = False


class HealthChecker:
    """Periodic health checks untuk model nodes."""

    def __init__(self, check_interval: float = 30.0, failure_threshold: int = 3, recovery_threshold: int = 2):
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        self._check_fn: Optional[Callable[[ModelNode], bool]] = None

    def set_check(self, fn: Callable[[ModelNode], bool]) -> None:
        self._check_fn = fn

    def check(self, node: ModelNode) -> bool:
        if not self._check_fn:
            return True
        try:
            healthy = self._check_fn(node)
            node.last_check = time.time()
            if healthy:
                node.success_count += 1
                node.failure_count = max(0, node.failure_count - 1)
                if node.status == NodeStatus.UNHEALTHY and node.success_count >= self.recovery_threshold:
                    node.status = NodeStatus.DEGRADED
                elif node.status == NodeStatus.DEGRADED and node.success_count >= self.recovery_threshold * 2:
                    node.status = NodeStatus.HEALTHY
            else:
                node.failure_count += 1
                node.success_count = 0
                if node.failure_count >= self.failure_threshold:
                    node.status = NodeStatus.UNHEALTHY
                elif node.failure_count >= self.failure_threshold // 2:
                    node.status = NodeStatus.DEGRADED
            return healthy
        except Exception:
            node.failure_count += 1
            node.last_check = time.time()
            return False

    def check_all(self, nodes: List[ModelNode]) -> Dict[str, bool]:
        return {node.node_id: self.check(node) for node in nodes}


class CircuitBreaker:
    """Circuit breaker untuk failing nodes."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0, half_open_max: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max

    def record_success(self, node: ModelNode) -> None:
        if node.circuit_state == CircuitState.HALF_OPEN:
            node.circuit_state = CircuitState.CLOSED
            node.circuit_failures = 0
        node.circuit_failures = max(0, node.circuit_failures - 1)

    def record_failure(self, node: ModelNode) -> None:
        node.circuit_failures += 1
        node.circuit_last_failure = time.time()
        if node.circuit_state == CircuitState.HALF_OPEN:
            node.circuit_state = CircuitState.OPEN
        elif node.circuit_failures >= self.failure_threshold:
            node.circuit_state = CircuitState.OPEN

    def can_attempt(self, node: ModelNode) -> bool:
        if node.circuit_state == CircuitState.CLOSED:
            return True
        if node.circuit_state == CircuitState.OPEN:
            if time.time() - node.circuit_last_failure > self.recovery_timeout:
                node.circuit_state = CircuitState.HALF_OPEN
                return True
            return False
        if node.circuit_state == CircuitState.HALF_OPEN:
            return node.circuit_failures < self.half_open_max
        return True


class LoadBalancer:
    """Route requests ke model nodes dengan berbagai strategies."""

    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN, health_checker: Optional[HealthChecker] = None):
        self.strategy = strategy
        self.health_checker = health_checker or HealthChecker()
        self.circuit_breaker = CircuitBreaker()
        self._nodes: Dict[str, ModelNode] = {}
        self._round_robin_index = 0
        self._routing_history: List[RoutingResult] = []

    def add_node(self, node: ModelNode) -> None:
        self._nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> bool:
        return self._nodes.pop(node_id, None) is not None

    def get_node(self, node_id: str) -> Optional[ModelNode]:
        return self._nodes.get(node_id)

    def route(self, request_metadata: Optional[Dict[str, Any]] = None) -> Optional[RoutingResult]:
        available = [n for n in self._nodes.values() if n.is_available() and self.circuit_breaker.can_attempt(n)]
        if not available:
            # Fallback: try any node that's not DOWN
            fallback = [n for n in self._nodes.values() if n.status != NodeStatus.DOWN]
            if not fallback:
                return None
            available = fallback
            fallback_used = True
        else:
            fallback_used = False

        if self.strategy == RoutingStrategy.ROUND_ROBIN:
            result = self._round_robin(available)
        elif self.strategy == RoutingStrategy.WEIGHTED:
            result = self._weighted(available)
        elif self.strategy == RoutingStrategy.LEAST_LATENCY:
            result = self._least_latency(available)
        elif self.strategy == RoutingStrategy.CAPACITY_BASED:
            result = self._capacity_based(available)
        elif self.strategy == RoutingStrategy.RANDOM:
            result = self._random(available)
        else:
            result = self._round_robin(available)

        if result:
            result.fallback_used = fallback_used
            self._routing_history.append(result)
            node = self._nodes.get(result.node_id)
            if node:
                node.current_load += 1
        return result

    def _round_robin(self, nodes: List[ModelNode]) -> Optional[RoutingResult]:
        if not nodes:
            return None
        self._round_robin_index = (self._round_robin_index + 1) % len(nodes)
        node = nodes[self._round_robin_index]
        return RoutingResult(node.node_id, RoutingStrategy.ROUND_ROBIN, node.avg_latency_ms)

    def _weighted(self, nodes: List[ModelNode]) -> Optional[RoutingResult]:
        if not nodes:
            return None
        total_weight = sum(n.weight for n in nodes)
        r = random.random() * total_weight
        cum = 0.0
        for node in nodes:
            cum += node.weight
            if r <= cum:
                return RoutingResult(node.node_id, RoutingStrategy.WEIGHTED, node.avg_latency_ms)
        return RoutingResult(nodes[-1].node_id, RoutingStrategy.WEIGHTED, nodes[-1].avg_latency_ms)

    def _least_latency(self, nodes: List[ModelNode]) -> Optional[RoutingResult]:
        if not nodes:
            return None
        node = min(nodes, key=lambda n: n.avg_latency_ms)
        return RoutingResult(node.node_id, RoutingStrategy.LEAST_LATENCY, node.avg_latency_ms)

    def _capacity_based(self, nodes: List[ModelNode]) -> Optional[RoutingResult]:
        if not nodes:
            return None
        node = max(nodes, key=lambda n: n.available_capacity())
        return RoutingResult(node.node_id, RoutingStrategy.CAPACITY_BASED, node.avg_latency_ms)

    def _random(self, nodes: List[ModelNode]) -> Optional[RoutingResult]:
        if not nodes:
            return None
        node = random.choice(nodes)
        return RoutingResult(node.node_id, RoutingStrategy.RANDOM, node.avg_latency_ms)

    def release(self, node_id: str) -> None:
        node = self._nodes.get(node_id)
        if node:
            node.current_load = max(0, node.current_load - 1)

    def report_success(self, node_id: str) -> None:
        node = self._nodes.get(node_id)
        if node:
            self.circuit_breaker.record_success(node)
            node.success_count += 1

    def report_failure(self, node_id: str, latency_ms: float = 0.0) -> None:
        node = self._nodes.get(node_id)
        if node:
            self.circuit_breaker.record_failure(node)
            node.failure_count += 1
            if latency_ms > 0:
                # Update avg latency with exponential moving average
                node.avg_latency_ms = 0.7 * node.avg_latency_ms + 0.3 * latency_ms

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._nodes)
        healthy = sum(1 for n in self._nodes.values() if n.status == NodeStatus.HEALTHY)
        total_load = sum(n.current_load for n in self._nodes.values())
        total_capacity = sum(n.max_capacity for n in self._nodes.values())
        return {
            "total_nodes": total,
            "healthy": healthy,
            "degraded": sum(1 for n in self._nodes.values() if n.status == NodeStatus.DEGRADED),
            "unhealthy": sum(1 for n in self._nodes.values() if n.status == NodeStatus.UNHEALTHY),
            "down": sum(1 for n in self._nodes.values() if n.status == NodeStatus.DOWN),
            "total_load": total_load,
            "total_capacity": total_capacity,
            "utilization": round(total_load / max(total_capacity, 1), 3),
            "strategy": self.strategy.name,
            "routing_history": len(self._routing_history)
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "name": n.name,
                        "status": n.status.name,
                        "circuit": n.circuit_state.name,
                        "load": n.current_load,
                        "capacity": n.max_capacity,
                        "latency_ms": round(n.avg_latency_ms, 2),
                        "success_rate": round(n.success_rate(), 3)
                    }
                    for n in self._nodes.values()
                ]
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("LOAD BALANCER DEMO")
    print("=" * 70)

    # 1. Round Robin
    print("\n[1] Round Robin Routing")
    lb = LoadBalancer(RoutingStrategy.ROUND_ROBIN)
    lb.add_node(ModelNode("n1", "GPT-4", weight=1.5, max_capacity=50, avg_latency_ms=120))
    lb.add_node(ModelNode("n2", "Claude-3", weight=1.2, max_capacity=40, avg_latency_ms=100))
    lb.add_node(ModelNode("n3", "LLaMA-3", weight=1.0, max_capacity=60, avg_latency_ms=80))
    for i in range(6):
        r = lb.route()
        print(f"  Request {i+1} -> {r.node_id} ({r.strategy.name})")
        lb.release(r.node_id)

    # 2. Weighted routing
    print("\n[2] Weighted Routing")
    lb2 = LoadBalancer(RoutingStrategy.WEIGHTED)
    lb2.add_node(ModelNode("n1", "GPT-4", weight=3.0, max_capacity=50))
    lb2.add_node(ModelNode("n2", "Claude-3", weight=2.0, max_capacity=40))
    lb2.add_node(ModelNode("n3", "LLaMA-3", weight=1.0, max_capacity=60))
    counts = {"n1": 0, "n2": 0, "n3": 0}
    for _ in range(1000):
        r = lb2.route()
        counts[r.node_id] += 1
        lb2.release(r.node_id)
    print(f"  Distribution over 1000 requests: {counts}")

    # 3. Least latency
    print("\n[3] Least Latency Routing")
    lb3 = LoadBalancer(RoutingStrategy.LEAST_LATENCY)
    lb3.add_node(ModelNode("n1", "Slow", avg_latency_ms=500, max_capacity=10))
    lb3.add_node(ModelNode("n2", "Fast", avg_latency_ms=50, max_capacity=10))
    for i in range(5):
        r = lb3.route()
        print(f"  Request {i+1} -> {r.node_id} (est_latency: {r.estimated_latency}ms)")
        lb3.release(r.node_id)

    # 4. Capacity-based
    print("\n[4] Capacity-Based Routing")
    lb4 = LoadBalancer(RoutingStrategy.CAPACITY_BASED)
    lb4.add_node(ModelNode("n1", "Node1", max_capacity=10, current_load=8))
    lb4.add_node(ModelNode("n2", "Node2", max_capacity=10, current_load=3))
    lb4.add_node(ModelNode("n3", "Node3", max_capacity=10, current_load=5))
    for i in range(5):
        r = lb4.route()
        node = lb4.get_node(r.node_id)
        print(f"  Request {i+1} -> {r.node_id} (avail_cap: {node.available_capacity()})")
        lb4.release(r.node_id)

    # 5. Circuit breaker
    print("\n[5] Circuit Breaker")
    lb5 = LoadBalancer(RoutingStrategy.ROUND_ROBIN)
    lb5.add_node(ModelNode("n1", "Stable", max_capacity=10))
    lb5.add_node(ModelNode("n2", "Fragile", max_capacity=10))
    # Simulate failures on n2
    for _ in range(6):
        lb5.report_failure("n2")
    print(f"  n2 circuit state: {lb5.get_node('n2').circuit_state.name}")
    r = lb5.route()
    print(f"  Route after failures: {r.node_id if r else 'None'} (fallback: {r.fallback_used if r else False})")
    # Simulate recovery
    for _ in range(3):
        lb5.report_success("n2")
    print(f"  n2 circuit state after recovery: {lb5.get_node('n2').circuit_state.name}")

    # 6. Health checks
    print("\n[6] Health Checks")
    checker = HealthChecker(failure_threshold=2, recovery_threshold=1)
    checker.set_check(lambda n: n.name != "Fragile")
    node = ModelNode("test", "Fragile")
    checker.check(node)
    checker.check(node)
    print(f"  Node status after 2 failures: {node.status.name}")
    checker.set_check(lambda n: True)
    checker.check(node)
    print(f"  Node status after 1 success: {node.status.name}")

    # 7. Stats
    print("\n[7] Load Balancer Stats")
    print(f"  {lb.get_stats()}")
    lb.export("/tmp/load_balancer.json")
    print(f"  Exported to /tmp/load_balancer.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
