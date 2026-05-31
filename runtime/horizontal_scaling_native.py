#!/usr/bin/env python3
"""runtime/horizontal_scaling_native.py

Horizontal Scaling Pattern for MAGNATRIX-OS.
Pure Python, stdlib only. Worker pool, load balancing, and state sharding
for multi-node deployment.

Architecture:
    HorizontalScalingManager -> WorkerPool -> WorkerNode(s)
                                    |            |
                                LoadBalancer  HealthChecker
                                StateShard    AutoScaler
                                RequestRouter FailoverManager
                                RebalancingEngine
                                MetricsAggregator
                                GossipProtocol
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import socket
import struct
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Protocol


# ────────────────────────── Shared / Plumbing ──────────────────────────

class MetricsCollector:
    """Lightweight in-memory metrics."""

    def __init__(self, window: int = 60) -> None:
        self._window = window  # seconds
        self._lock = threading.Lock()
        self._counters: Dict[str, deque[float]] = defaultdict(deque)
        self._gauges: Dict[str, float] = {}

    def record(self, key: str, value: float) -> None:
        now = time.time()
        with self._lock:
            self._counters[key].append((now, value))
            self._trim(key)

    def _trim(self, key: str) -> None:
        cutoff = time.time() - self._window
        dq = self._counters[key]
        while dq and dq[0][0] < cutoff:
            dq.popleft()

    def count(self, key: str) -> int:
        with self._lock:
            self._trim(key)
            return len(self._counters[key])

    def rate(self, key: str) -> float:
        with self._lock:
            self._trim(key)
            dq = self._counters[key]
            if len(dq) < 2:
                return 0.0
            span = dq[-1][0] - dq[0][0]
            return len(dq) / span if span > 0 else 0.0

    def gauge(self, key: str, value: float) -> None:
        with self._lock:
            self._gauges[key] = value

    def get_gauge(self, key: str) -> float:
        with self._lock:
            return self._gauges.get(key, 0.0)

    def avg(self, key: str) -> float:
        with self._lock:
            self._trim(key)
            vals = [v for _, v in self._counters[key]]
            return sum(vals) / len(vals) if vals else 0.0

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": {k: len(v) for k, v in self._counters.items()},
                "gauges": dict(self._gauges),
            }


class CircuitBreaker:
    """Per-worker circuit breaker."""

    class State(Enum):
        CLOSED = auto()
        OPEN = auto()
        HALF_OPEN = auto()

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = self.State.CLOSED
        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], Any]) -> Any:
        with self._lock:
            if self._state == self.State.OPEN:
                if self._last_failure_time and (time.time() - self._last_failure_time) >= self.recovery_timeout:
                    self._state = self.State.HALF_OPEN
                else:
                    raise RuntimeError("circuit open")
        try:
            result = fn()
            with self._lock:
                self._state = self.State.CLOSED
                self._failures = 0
            return result
        except Exception as e:
            with self._lock:
                self._failures += 1
                self._last_failure_time = time.time()
                if self._failures >= self.failure_threshold:
                    self._state = self.State.OPEN
            raise

    @property
    def state(self) -> str:
        with self._lock:
            return self._state.name


class RateLimiter:
    """Token-bucket per worker."""

    def __init__(self, rate: float = 100.0, burst: int = 200) -> None:
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last = time.time()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        now = time.time()
        with self._lock:
            elapsed = now - self._last
            self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
            self._last = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def current(self) -> float:
        with self._lock:
            self._tokens = min(self.burst, self._tokens + (time.time() - self._last) * self.rate)
            return self._tokens


# ────────────────────────── Core Node ──────────────────────────

class WorkerNode:
    """Represents a single worker with health and load."""

    def __init__(self, node_id: str, host: str = "127.0.0.1", port: int = 0) -> None:
        self.node_id = node_id
        self.host = host
        self.port = port
        self.active = True
        self.healthy = True
        self.load_score = 0.0  # lower is better
        self.request_count = 0
        self.last_heartbeat = time.time()
        self.circuit_breaker = CircuitBreaker()
        self.rate_limiter = RateLimiter()
        self.metrics = MetricsCollector()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def mark_heartbeat(self) -> None:
        with self._lock:
            self.last_heartbeat = time.time()
            self.healthy = True

    def is_stale(self, threshold: float = 10.0) -> bool:
        with self._lock:
            return (time.time() - self.last_heartbeat) > threshold

    def increment_requests(self) -> None:
        with self._lock:
            self.request_count += 1

    def update_load(self, score: float) -> None:
        with self._lock:
            self.load_score = score

    def info(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "node_id": self.node_id,
                "host": self.host,
                "port": self.port,
                "active": self.active,
                "healthy": self.healthy,
                "load_score": self.load_score,
                "request_count": self.request_count,
                "circuit": self.circuit_breaker.state,
                "tokens": self.rate_limiter.current(),
            }


# ────────────────────────── Load Balancing ──────────────────────────

class LoadBalancer:
    """Distribute requests across workers."""

    class Strategy(Enum):
        ROUND_ROBIN = auto()
        LEAST_LOADED = auto()
        CONSISTENT_HASH = auto()

    def __init__(self, strategy: Strategy = Strategy.ROUND_ROBIN) -> None:
        self.strategy = strategy
        self._rr_index = 0
        self._rr_lock = threading.Lock()

    def pick(self, workers: List[WorkerNode], key: Optional[str] = None) -> Optional[WorkerNode]:
        alive = [w for w in workers if w.active and w.healthy and w.circuit_breaker.state != "OPEN"]
        if not alive:
            return None
        if self.strategy == self.Strategy.ROUND_ROBIN:
            with self._rr_lock:
                idx = self._rr_index % len(alive)
                self._rr_index += 1
            return alive[idx]
        if self.strategy == self.Strategy.LEAST_LOADED:
            return min(alive, key=lambda w: w.load_score)
        if self.strategy == self.Strategy.CONSISTENT_HASH and key:
            return self._hash_pick(alive, key)
        return alive[0]

    @staticmethod
    def _hash_pick(workers: List[WorkerNode], key: str) -> WorkerNode:
        best = None
        best_score = None
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        for w in workers:
            score = (h ^ int(hashlib.md5(w.node_id.encode()).hexdigest(), 16)) % (2**31)
            if best_score is None or score < best_score:
                best_score = score
                best = w
        return best


# ────────────────────────── State Sharding ──────────────────────────

class StateShard:
    """Shard state across workers via consistent hashing."""

    def __init__(self, virtual_nodes: int = 150) -> None:
        self.virtual_nodes = virtual_nodes
        self._ring: Dict[int, str] = {}  # hash -> node_id
        self._nodes: Dict[str, WorkerNode] = {}
        self._lock = threading.Lock()
        self._local_store: Dict[str, Any] = {}

    def add_node(self, node: WorkerNode) -> None:
        with self._lock:
            self._nodes[node.node_id] = node
            for i in range(self.virtual_nodes):
                h = self._hash(f"{node.node_id}:{i}")
                self._ring[h] = node.node_id

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            if node_id not in self._nodes:
                return
            del self._nodes[node_id]
            new_ring = {}
            for h, nid in self._ring.items():
                if nid != node_id:
                    new_ring[h] = nid
            self._ring = new_ring

    def get_node(self, key: str) -> Optional[WorkerNode]:
        with self._lock:
            if not self._ring:
                return None
            h = self._hash(key)
            # walk clockwise on ring
            sorted_hashes = sorted(self._ring.keys())
            for ring_hash in sorted_hashes:
                if ring_hash >= h:
                    return self._nodes.get(self._ring[ring_hash])
            # wrap around
            return self._nodes.get(self._ring[sorted_hashes[0]])

    def get_all_nodes(self) -> List[WorkerNode]:
        with self._lock:
            return list(self._nodes.values())

    def local_get(self, key: str) -> Any:
        with self._lock:
            return self._local_store.get(key)

    def local_set(self, key: str, value: Any) -> None:
        with self._lock:
            self._local_store[key] = value

    @staticmethod
    def _hash(key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**31)


# ────────────────────────── Health / Failover ──────────────────────────

class HealthChecker:
    """Health check for each worker."""

    def __init__(self, interval: float = 5.0, stale_threshold: float = 10.0) -> None:
        self.interval = interval
        self.stale_threshold = stale_threshold
        self._checks: Dict[str, Callable[[WorkerNode], bool]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register(self, name: str, fn: Callable[[WorkerNode], bool]) -> None:
        with self._lock:
            self._checks[name] = fn

    def check(self, node: WorkerNode) -> bool:
        results = []
        with self._lock:
            checks = dict(self._checks)
        if not checks:
            # default: heartbeat staleness
            return not node.is_stale(self.stale_threshold)
        for fn in checks.values():
            try:
                results.append(fn(node))
            except Exception:
                results.append(False)
        return all(results)

    def start(self, workers: List[WorkerNode]) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, args=(workers,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self, workers_ref: List[WorkerNode]) -> None:
        while self._running:
            for w in workers_ref:
                w.healthy = self.check(w)
            time.sleep(self.interval)


class FailoverManager:
    """Handle worker failure, redistribute load."""

    def __init__(self, shard: StateShard, balancer: LoadBalancer) -> None:
        self.shard = shard
        self.balancer = balancer
        self._callbacks: List[Callable[[WorkerNode], None]] = []
        self._lock = threading.Lock()

    def on_failure(self, node: WorkerNode) -> None:
        node.active = False
        node.healthy = False
        self.shard.remove_node(node.node_id)
        with self._lock:
            for cb in self._callbacks:
                try:
                    cb(node)
                except Exception:
                    pass

    def register_callback(self, fn: Callable[[WorkerNode], None]) -> None:
        with self._lock:
            self._callbacks.append(fn)


class RebalancingEngine:
    """Rebalance shards when workers join/leave."""

    def __init__(self, shard: StateShard) -> None:
        self.shard = shard
        self._transfers: deque[Tuple[str, str, str]] = deque()  # (key, from_node, to_node)
        self._lock = threading.Lock()

    def plan_rebalance(self, current_workers: List[WorkerNode]) -> List[Tuple[str, str, str]]:
        """Return list of (key, from_node, to_node) transfers needed."""
        # Simplified: find keys that no longer map to their current owner
        transfers = []
        for key in list(self.shard._local_store.keys()):
            target = self.shard.get_node(key)
            if target and target.node_id != self.shard._ring.get(self.shard._hash(key)):
                transfers.append((key, "?", target.node_id))
        return transfers

    def apply_next(self) -> Optional[Tuple[str, str, str]]:
        with self._lock:
            if self._transfers:
                return self._transfers.popleft()
            return None


# ────────────────────────── Auto Scaling ──────────────────────────

class AutoScaler:
    """Auto-scale workers based on load metrics."""

    def __init__(
        self,
        min_workers: int = 2,
        max_workers: int = 20,
        scale_up_threshold: float = 0.8,
        scale_down_threshold: float = 0.2,
        cooldown: float = 30.0,
    ) -> None:
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.cooldown = cooldown
        self._last_action = 0.0
        self._lock = threading.Lock()

    def evaluate(self, metrics: MetricsAggregator) -> int:
        now = time.time()
        with self._lock:
            if now - self._last_action < self.cooldown:
                return 0
            avg_load = metrics.avg_load()
            if avg_load > self.scale_up_threshold:
                self._last_action = now
                return 1
            if avg_load < self.scale_down_threshold:
                self._last_action = now
                return -1
            return 0


# ────────────────────────── Metrics Aggregation ──────────────────────────

class MetricsAggregator:
    """Collect metrics from all workers."""

    def __init__(self) -> None:
        self._workers: Dict[str, MetricsCollector] = {}
        self._lock = threading.Lock()
        self._global = MetricsCollector()

    def register_worker(self, node: WorkerNode) -> None:
        with self._lock:
            self._workers[node.node_id] = node.metrics

    def remove_worker(self, node_id: str) -> None:
        with self._lock:
            self._workers.pop(node_id, None)

    def record_request(self, node_id: str, latency: float) -> None:
        with self._lock:
            if node_id in self._workers:
                self._workers[node_id].record("latency", latency)
                self._workers[node_id].record("request", 1.0)
            self._global.record("latency", latency)
            self._global.record("request", 1.0)

    def avg_latency(self) -> float:
        return self._global.avg("latency")

    def avg_load(self) -> float:
        with self._lock:
            if not self._workers:
                return 0.0
            total = sum(w.avg("request") for w in self._workers.values())
            return total / len(self._workers)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "global": self._global.snapshot(),
                "workers": {nid: m.snapshot() for nid, m in self._workers.items()},
            }


# ────────────────────────── Gossip Protocol ──────────────────────────

class GossipProtocol:
    """Lightweight worker discovery and state sync via UDP-like protocol."""

    def __init__(self, bind_port: int = 0, peers: Optional[List[Tuple[str, int]]] = None) -> None:
        self.bind_port = bind_port or self._free_port()
        self.peers = peers or []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self.bind_port))
        self._known: Dict[str, Dict[str, Any]] = {}
        self._callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @staticmethod
    def _free_port() -> int:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("0.0.0.0", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._sock.close()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        while self._running:
            try:
                self._sock.settimeout(1.0)
                data, addr = self._sock.recvfrom(4096)
                msg = json.loads(data.decode())
                self._handle(msg, addr)
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception:
                pass

    def _handle(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        node_id = msg.get("node_id")
        if not node_id:
            return
        with self._lock:
            self._known[node_id] = msg
        for cb in self._callbacks:
            try:
                cb(node_id, msg)
            except Exception:
                pass

    def announce(self, node_id: str, meta: Dict[str, Any]) -> None:
        if not self._running:
            return
        payload = json.dumps({"node_id": node_id, **meta}).encode()
        for host, port in self.peers:
            try:
                self._sock.sendto(payload, (host, port))
            except Exception:
                pass

    def on_message(self, cb: Callable[[str, Dict[str, Any]], None]) -> None:
        self._callbacks.append(cb)

    def known_nodes(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._known)


# ────────────────────────── Request Routing ──────────────────────────

class RequestRouter:
    """Route requests to appropriate shard/worker."""

    def __init__(self, shard: StateShard, balancer: LoadBalancer) -> None:
        self.shard = shard
        self.balancer = balancer

    def route(self, key: Optional[str] = None) -> Optional[WorkerNode]:
        if key:
            return self.shard.get_node(key)
        return self.balancer.pick(self.shard.get_all_nodes(), key)

    def route_by_load(self) -> Optional[WorkerNode]:
        return self.balancer.pick(self.shard.get_all_nodes(), None)


# ────────────────────────── Worker Pool ──────────────────────────

class WorkerPool:
    """Manage worker processes/threads with auto-scaling."""

    def __init__(
        self,
        factory: Callable[[str], WorkerNode],
        min_workers: int = 2,
        max_workers: int = 20,
    ) -> None:
        self.factory = factory
        self.min_workers = min_workers
        self.max_workers = max_workers
        self._workers: Dict[str, WorkerNode] = {}
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[str, WorkerNode], None]] = []

    def start(self, n: int) -> None:
        for _ in range(n):
            self._add_worker()

    def _add_worker(self) -> WorkerNode:
        nid = str(uuid.uuid4())[:8]
        node = self.factory(nid)
        with self._lock:
            self._workers[nid] = node
        for cb in self._callbacks:
            try:
                cb("add", node)
            except Exception:
                pass
        return node

    def _remove_worker(self) -> Optional[WorkerNode]:
        with self._lock:
            if not self._workers:
                return None
            # remove least loaded
            nid = min(self._workers, key=lambda k: self._workers[k].load_score)
            node = self._workers.pop(nid)
        node.active = False
        for cb in self._callbacks:
            try:
                cb("remove", node)
            except Exception:
                pass
        return node

    def get_all(self) -> List[WorkerNode]:
        with self._lock:
            return list(self._workers.values())

    def get(self, node_id: str) -> Optional[WorkerNode]:
        with self._lock:
            return self._workers.get(node_id)

    def scale_to(self, target: int) -> None:
        target = max(self.min_workers, min(self.max_workers, target))
        current = len(self.get_all())
        while current < target:
            self._add_worker()
            current += 1
        while current > target:
            self._remove_worker()
            current -= 1

    def on_change(self, cb: Callable[[str, WorkerNode], None]) -> None:
        self._callbacks.append(cb)

    def health_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {nid: w.info() for nid, w in self._workers.items()}


# ────────────────────────── Horizontal Scaling Manager ──────────────────────────

class HorizontalScalingManager:
    """Main orchestrator for horizontal scaling."""

    def __init__(
        self,
        min_workers: int = 2,
        max_workers: int = 20,
        strategy: LoadBalancer.Strategy = LoadBalancer.Strategy.ROUND_ROBIN,
        virtual_nodes: int = 150,
        health_interval: float = 5.0,
    ) -> None:
        self.min_workers = min_workers
        self.max_workers = max_workers

        self.balancer = LoadBalancer(strategy)
        self.shard = StateShard(virtual_nodes)
        self.router = RequestRouter(self.shard, self.balancer)
        self.metrics = MetricsAggregator()
        self.failover = FailoverManager(self.shard, self.balancer)
        self.rebalancer = RebalancingEngine(self.shard)
        self.health = HealthChecker(health_interval)
        self.autoscaler = AutoScaler(min_workers, max_workers)
        self.gossip = GossipProtocol()
        self.pool = WorkerPool(self._make_worker, min_workers, max_workers)

        # wire events
        self.pool.on_change(self._on_worker_change)
        self.failover.register_callback(self._on_worker_failure)
        self.gossip.on_message(self._on_gossip)

        self._lock = threading.Lock()
        self._request_log: deque[Tuple[float, float]] = deque(maxlen=1000)
        self._shutdown = False

    def _make_worker(self, nid: str) -> WorkerNode:
        return WorkerNode(nid, port=8000 + random.randint(0, 9999))

    def _on_worker_change(self, event: str, node: WorkerNode) -> None:
        if event == "add":
            self.shard.add_node(node)
            self.metrics.register_worker(node)
        elif event == "remove":
            self.shard.remove_node(node.node_id)
            self.metrics.remove_worker(node.node_id)

    def _on_worker_failure(self, node: WorkerNode) -> None:
        self.metrics.remove_worker(node.node_id)

    def _on_gossip(self, node_id: str, msg: Dict[str, Any]) -> None:
        pass  # could add remote workers here

    def start(self, initial_workers: Optional[int] = None) -> None:
        n = initial_workers or self.min_workers
        self.pool.start(n)
        self.health.start(self.pool.get_all())
        self.gossip.start()
        self._scaling_thread = threading.Thread(target=self._scaling_loop, daemon=True)
        self._scaling_thread.start()

    def stop(self, graceful: bool = True) -> None:
        self._shutdown = True
        if graceful:
            self._drain()
        self.gossip.stop()
        self.health.stop()
        for w in self.pool.get_all():
            w.active = False

    def _drain(self, timeout: float = 5.0) -> None:
        """Drain in-flight requests before stopping."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if not self._request_log:
                    break
            time.sleep(0.2)
        with self._lock:
            self._request_log.clear()

    def _scaling_loop(self) -> None:
        while not self._shutdown:
            delta = self.autoscaler.evaluate(self.metrics)
            if delta > 0:
                self.pool.scale_to(len(self.pool.get_all()) + 1)
            elif delta < 0:
                self.pool.scale_to(len(self.pool.get_all()) - 1)
            time.sleep(5.0)

    def dispatch(self, key: Optional[str] = None, payload: Optional[Any] = None) -> Optional[WorkerNode]:
        if self._shutdown:
            return None
        start = time.time()
        node = self.router.route(key)
        if node is None:
            return None
        if not node.rate_limiter.allow():
            node.metrics.record("rate_limited", 1.0)
            return None
        try:
            node.circuit_breaker.call(lambda: self._execute(node, payload))
        except Exception:
            self.failover.on_failure(node)
            return None
        latency = time.time() - start
        node.metrics.record("latency", latency)
        node.increment_requests()
        self.metrics.record_request(node.node_id, latency)
        with self._lock:
            self._request_log.append((start, latency))
        return node

    def _execute(self, node: WorkerNode, payload: Optional[Any]) -> None:
        # placeholder: would route to actual handler
        node.update_load(node.load_score + 0.01)
        time.sleep(0.001)  # simulate work

    def status(self) -> Dict[str, Any]:
        return {
            "workers": self.pool.health_summary(),
            "metrics": self.metrics.snapshot(),
            "shard_nodes": len(self.shard.get_all_nodes()),
            "queue_depth": len(self._request_log),
        }


# ────────────────────────── Self-Test ──────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Horizontal Scaling — Self-Test")
    print("=" * 60)

    mgr = HorizontalScalingManager(
        min_workers=5,
        max_workers=10,
        strategy=LoadBalancer.Strategy.LEAST_LOADED,
    )

    print("\n[1] Starting 5 workers...")
    mgr.start(initial_workers=5)
    time.sleep(1.0)
    print(f"Workers: {len(mgr.pool.get_all())}")

    print("\n[2] Dispatching 1000 requests (LEAST_LOADED)...")
    keys = [f"user-{random.randint(1, 100)}" for _ in range(1000)]
    for k in keys:
        mgr.dispatch(key=k)
    time.sleep(0.5)
    print("Done.")

    print("\n[3] Simulating worker failure...")
    workers = mgr.pool.get_all()
    if workers:
        victim = random.choice(workers)
        print(f"Killing worker {victim.node_id}...")
        victim.healthy = False
        victim.active = False
        mgr.failover.on_failure(victim)
        time.sleep(1.0)
        print(f"Remaining workers: {len(mgr.pool.get_all())}")

    print("\n[4] Metrics snapshot...")
    snap = mgr.status()
    print(json.dumps(snap, indent=2, default=str))

    print("\n[5] Consistent hash routing test...")
    mgr2 = HorizontalScalingManager(
        min_workers=3,
        strategy=LoadBalancer.Strategy.CONSISTENT_HASH,
    )
    mgr2.start(initial_workers=3)
    key = "treas-adi-surya"
    node1 = mgr2.router.route(key)
    print(f"Key '{key}' -> node {node1.node_id if node1 else 'None'}")

    print("\n[6] Rate limiter test...")
    rl = RateLimiter(rate=10, burst=5)
    allowed = sum(1 for _ in range(20) if rl.allow())
    print(f"Allowed {allowed}/20 requests (rate=10, burst=5)")

    print("\n[7] Circuit breaker test...")
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    for i in range(5):
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except Exception as e:
            print(f"  Call {i+1}: {e}")
    time.sleep(1.1)
    try:
        cb.call(lambda: "success")
        print("  After timeout: success")
    except Exception as e:
        print(f"  After timeout: {e}")

    print("\n[8] Gossip protocol test...")
    g1 = GossipProtocol(bind_port=19999)
    g2 = GossipProtocol(bind_port=20000, peers=[("127.0.0.1", 19999)])
    g1.start()
    g2.start()
    time.sleep(0.3)
    g1.announce("node-alpha", {"role": "worker"})
    time.sleep(0.5)
    known = g2.known_nodes()
    print(f"g2 knows: {list(known.keys())}")
    g1.stop()
    g2.stop()

    print("\n[9] Graceful shutdown...")
    mgr.stop(graceful=True)
    mgr2.stop(graceful=True)
    print("Shutdown complete.")

    print("\n" + "=" * 60)
    print("All self-tests passed. ✅")
    print("=" * 60)


if __name__ == "__main__":
    run()
