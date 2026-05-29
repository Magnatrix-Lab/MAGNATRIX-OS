#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 4 — Load Balancer
Native load balancer with multiple strategies and health-aware routing.
- Round-robin, weighted, least-connections, consistent hashing
- Health-aware filtering (exclude unhealthy backends)
- Sticky sessions via hash ring
- Automatic retry with exponential backoff
"""
import hashlib, time, threading, random, os, sys, json
from typing import Dict, List, Optional, Callable, Any, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class Backend:
    id: str
    host: str
    port: int
    weight: int = 1
    connections: int = 0
    healthy: bool = True
    last_check: float = 0.0


class Strategy:
    """Base load balancing strategy."""

    def select(self, backends: List[Backend]) -> Optional[Backend]:
        raise NotImplementedError


class RoundRobin(Strategy):
    """Simple round-robin."""

    def __init__(self):
        self._index = 0
        self._lock = threading.Lock()

    def select(self, backends: List[Backend]) -> Optional[Backend]:
        healthy = [b for b in backends if b.healthy]
        if not healthy:
            return None
        with self._lock:
            idx = self._index % len(healthy)
            self._index = (self._index + 1) % len(healthy)
            return healthy[idx]


class WeightedRoundRobin(Strategy):
    """Weighted round-robin using smooth weighted algorithm."""

    def __init__(self):
        self._current_weights: Dict[str, int] = {}
        self._lock = threading.Lock()

    def select(self, backends: List[Backend]) -> Optional[Backend]:
        healthy = [b for b in backends if b.healthy]
        if not healthy:
            return None
        with self._lock:
            total = 0
            best = None
            for b in healthy:
                cw = self._current_weights.get(b.id, 0) + b.weight
                self._current_weights[b.id] = cw
                total += b.weight
                if best is None or cw > self._current_weights.get(best.id, 0):
                    best = b
            if best:
                self._current_weights[best.id] -= total
            return best


class LeastConnections(Strategy):
    """Select backend with fewest active connections."""

    def select(self, backends: List[Backend]) -> Optional[Backend]:
        healthy = [b for b in backends if b.healthy]
        if not healthy:
            return None
        return min(healthy, key=lambda b: b.connections)


class ConsistentHash(Strategy):
    """Consistent hashing for sticky sessions."""

    def __init__(self, replicas: int = 150):
        self.replicas = replicas
        self._ring: Dict[int, str] = {}
        self._backends: Dict[str, Backend] = {}
        self._lock = threading.Lock()

    def _hash(self, key: str) -> int:
        return int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)

    def add_backend(self, backend: Backend):
        with self._lock:
            self._backends[backend.id] = backend
            for i in range(self.replicas):
                h = self._hash(f"{backend.id}:{i}")
                self._ring[h] = backend.id

    def remove_backend(self, backend_id: str):
        with self._lock:
            if backend_id in self._backends:
                del self._backends[backend_id]
            to_remove = [h for h, bid in self._ring.items() if bid == backend_id]
            for h in to_remove:
                del self._ring[h]

    def select(self, key: str) -> Optional[Backend]:
        with self._lock:
            if not self._ring:
                return None
            h = self._hash(key)
            # Find next node on ring
            sorted_hashes = sorted(self._ring.keys())
            for ring_hash in sorted_hashes:
                if ring_hash >= h:
                    bid = self._ring[ring_hash]
                    return self._backends.get(bid)
            # Wrap around
            bid = self._ring[sorted_hashes[0]]
            return self._backends.get(bid)


class RetryPolicy:
    """Exponential backoff retry policy."""

    def __init__(self, max_retries: int = 3, base_delay: float = 0.1, max_delay: float = 2.0, backoff: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff = backoff

    def execute(self, fn: Callable, *args, **kwargs) -> Any:
        delay = self.base_delay
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(min(delay, self.max_delay))
                    delay *= self.backoff
        raise last_error


class NativeLoadBalancer:
    """Full load balancer with strategy selection and health filtering."""

    STRATEGIES = {
        "round_robin": RoundRobin,
        "weighted": WeightedRoundRobin,
        "least_connections": LeastConnections,
        "consistent_hash": ConsistentHash,
    }

    def __init__(self, strategy: str = "round_robin"):
        self._backends: Dict[str, Backend] = {}
        self._strategy: Strategy = self.STRATEGIES.get(strategy, RoundRobin)()
        self._lock = threading.Lock()
        self._retry = RetryPolicy()

    def add(self, backend: Backend):
        with self._lock:
            self._backends[backend.id] = backend
            if isinstance(self._strategy, ConsistentHash):
                self._strategy.add_backend(backend)

    def remove(self, backend_id: str):
        with self._lock:
            if backend_id in self._backends:
                del self._backends[backend_id]
            if isinstance(self._strategy, ConsistentHash):
                self._strategy.remove_backend(backend_id)

    def set_health(self, backend_id: str, healthy: bool):
        with self._lock:
            if backend_id in self._backends:
                self._backends[backend_id].healthy = healthy
                self._backends[backend_id].last_check = time.time()

    def select(self, key: str = "") -> Optional[Backend]:
        with self._lock:
            backends = list(self._backends.values())
        if isinstance(self._strategy, ConsistentHash):
            return self._strategy.select(key)
        return self._strategy.select(backends)

    def route(self, key: str, fn: Callable, *args, **kwargs) -> Any:
        backend = self.select(key)
        if not backend:
            raise Exception("No healthy backend available")
        backend.connections += 1
        try:
            return self._retry.execute(fn, *args, **kwargs)
        finally:
            backend.connections -= 1

    def stats(self) -> Dict:
        with self._lock:
            backends = list(self._backends.values())
        return {
            "total": len(backends),
            "healthy": sum(1 for b in backends if b.healthy),
            "unhealthy": sum(1 for b in backends if not b.healthy),
            "total_connections": sum(b.connections for b in backends),
            "strategy": self._strategy.__class__.__name__,
        }

    def set_strategy(self, name: str):
        with self._lock:
            self._strategy = self.STRATEGIES.get(name, RoundRobin)()
            if isinstance(self._strategy, ConsistentHash):
                for b in self._backends.values():
                    self._strategy.add_backend(b)


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("round_robin", lambda: RoundRobin().select([Backend("a", "1", 80), Backend("b", "2", 80)]) is not None)
    _t("weighted", lambda: WeightedRoundRobin().select([Backend("a", "1", 80, weight=5), Backend("b", "2", 80, weight=1)]) is not None)
    _t("least_conn", lambda: LeastConnections().select([Backend("a", "1", 80, connections=10), Backend("b", "2", 80, connections=1)]).id == "b")
    _t("consistent_hash", lambda: (ch := ConsistentHash(), ch.add_backend(Backend("a", "1", 80)), ch.select("key") is not None)[2])
    _t("hash_sticky", lambda: (ch := ConsistentHash(), ch.add_backend(Backend("a", "1", 80)), ch.add_backend(Backend("b", "2", 80)), ch.select("x") == ch.select("x"))[3])
    _t("retry_ok", lambda: RetryPolicy().execute(lambda: "ok") == "ok")
    _t("retry_fail", lambda: (RetryPolicy(max_retries=1, base_delay=0.01).execute(lambda: (_ for _ in ()).throw(Exception("x"))) or False))
    _t("lb_add_select", lambda: (lb := NativeLoadBalancer(), lb.add(Backend("a", "1", 80)), lb.select() is not None)[2])
    _t("lb_health_filter", lambda: (lb := NativeLoadBalancer(), lb.add(Backend("a", "1", 80, healthy=False)), lb.select() is None)[2])
    _t("lb_stats", lambda: "total" in NativeLoadBalancer().stats())

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nLoad Balancer: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
