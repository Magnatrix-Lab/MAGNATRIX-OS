#!/usr/bin/env python3
"""
MAGNATRIX-OS — Rate Limiting & Cache Engine
ai/llm_rate_limiting_cache_native.py

Provides:
- Token bucket rate limiter (per-client, configurable burst/refill)
- Sliding window counter (rolling window request counting)
- Request cache with TTL (in-memory, key-based, auto-expiry)
- Circuit breaker pattern (open / half-open / closed)
- Distributed rate limiting simulation (consistent hash ring, multi-node)
- Unified Manager tying all components together

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
import random
import threading
import time
import timeit
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Protocol, Set, Tuple

# ────────────────────────────────
# Logging
# ────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("rate_limit_cache")


# ────────────────────────────────
# Enums
# ────────────────────────────────

class CircuitState(enum.Enum):
    CLOSED = "closed"          # requests flow normally
    OPEN = "open"              # circuit broken; requests rejected immediately
    HALF_OPEN = "half_open"    # probing one request at a time


class RateLimitDecision(enum.Enum):
    ALLOW = "allow"
    DENY = "deny"


class CacheResult(enum.Enum):
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"


# ────────────────────────────────
# Data models
# ────────────────────────────────

@dataclass(frozen=True)
class ClientKey:
    """Immutable client identifier."""
    client_id: str


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit policy."""
    burst: int           # max tokens in bucket
    refill_rate: float   # tokens added per second
    window_seconds: int  # sliding window size
    window_max: int      # max requests in rolling window


@dataclass
class CacheEntry:
    """A single cache entry with TTL."""
    value: Any
    created_at: float
    ttl_seconds: float
    access_count: int = 0

    def is_expired(self, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.monotonic()
        return (now - self.created_at) > self.ttl_seconds


@dataclass
class TokenBucketState:
    """Mutable state of a token bucket."""
    tokens: float
    last_refill: float
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class SlidingWindowState:
    """Mutable state of a sliding window counter."""
    timestamps: Deque[float] = field(default_factory=lambda: deque())
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class CircuitBreakerState:
    """Mutable state of a circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class RateLimitReport:
    """Report from a single rate-limit check."""
    decision: RateLimitDecision
    client: str
    bucket_tokens: float
    window_count: int
    reason: str


@dataclass
class CacheReport:
    """Report from a single cache lookup."""
    result: CacheResult
    key: str
    value: Optional[Any] = None
    age_seconds: float = 0.0


# ────────────────────────────────
# 1. Token Bucket Rate Limiter
# ────────────────────────────────

class TokenBucketRateLimiter:
    """
    Per-client token bucket rate limiter.
    Each client gets its own bucket with configurable burst and refill rate.
    """

    def __init__(self, default_config: RateLimitConfig) -> None:
        self._default_config = default_config
        self._buckets: Dict[str, TokenBucketState] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._lock = threading.Lock()

    def _get_or_create_bucket(self, client_id: str) -> Tuple[TokenBucketState, RateLimitConfig]:
        with self._lock:
            config = self._configs.get(client_id, self._default_config)
            if client_id not in self._buckets:
                self._buckets[client_id] = TokenBucketState(
                    tokens=float(config.burst),
                    last_refill=time.monotonic(),
                )
            return self._buckets[client_id], config

    def allow(self, client_id: str, cost: float = 1.0) -> RateLimitReport:
        """Attempt to consume `cost` tokens for `client_id`."""
        bucket, config = self._get_or_create_bucket(client_id)
        now = time.monotonic()

        with bucket.lock:
            # Refill tokens based on elapsed time
            elapsed = now - bucket.last_refill
            refill = elapsed * config.refill_rate
            bucket.tokens = min(bucket.tokens + refill, float(config.burst))
            bucket.last_refill = now

            if bucket.tokens >= cost:
                bucket.tokens -= cost
                return RateLimitReport(
                    decision=RateLimitDecision.ALLOW,
                    client=client_id,
                    bucket_tokens=bucket.tokens,
                    window_count=0,  # not tracked here
                    reason="token_consumed",
                )
            else:
                return RateLimitReport(
                    decision=RateLimitDecision.DENY,
                    client=client_id,
                    bucket_tokens=bucket.tokens,
                    window_count=0,
                    reason="insufficient_tokens",
                )

    def set_config(self, client_id: str, config: RateLimitConfig) -> None:
        with self._lock:
            self._configs[client_id] = config
            # Reset bucket so new config takes effect immediately
            if client_id in self._buckets:
                self._buckets[client_id].tokens = float(config.burst)
                self._buckets[client_id].last_refill = time.monotonic()

    def get_state(self, client_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            bucket = self._buckets.get(client_id)
            if not bucket:
                return None
            with bucket.lock:
                return {
                    "tokens": round(bucket.tokens, 2),
                    "last_refill": bucket.last_refill,
                    "config": self._configs.get(client_id, self._default_config),
                }

    def remove_client(self, client_id: str) -> None:
        with self._lock:
            self._buckets.pop(client_id, None)
            self._configs.pop(client_id, None)

    def all_clients(self) -> List[str]:
        with self._lock:
            return list(self._buckets.keys())


# ────────────────────────────────
# 2. Sliding Window Counter
# ────────────────────────────────

class SlidingWindowCounter:
    """
    Rolling window request counter for rate limiting.
    Tracks timestamps within a configurable window and rejects if count exceeds limit.
    """

    def __init__(self, default_config: RateLimitConfig) -> None:
        self._default_config = default_config
        self._windows: Dict[str, SlidingWindowState] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._lock = threading.Lock()

    def _get_or_create_window(self, client_id: str) -> Tuple[SlidingWindowState, RateLimitConfig]:
        with self._lock:
            config = self._configs.get(client_id, self._default_config)
            if client_id not in self._windows:
                self._windows[client_id] = SlidingWindowState()
            return self._windows[client_id], config

    def allow(self, client_id: str) -> RateLimitReport:
        """Check if client is within rolling window limit."""
        window, config = self._get_or_create_window(client_id)
        now = time.monotonic()
        cutoff = now - config.window_seconds

        with window.lock:
            # Evict old timestamps outside the window
            while window.timestamps and window.timestamps[0] < cutoff:
                window.timestamps.popleft()

            count = len(window.timestamps)
            if count >= config.window_max:
                return RateLimitReport(
                    decision=RateLimitDecision.DENY,
                    client=client_id,
                    bucket_tokens=0.0,
                    window_count=count,
                    reason="window_full",
                )
            else:
                window.timestamps.append(now)
                return RateLimitReport(
                    decision=RateLimitDecision.ALLOW,
                    client=client_id,
                    bucket_tokens=0.0,
                    window_count=count + 1,
                    reason="window_accepted",
                )

    def set_config(self, client_id: str, config: RateLimitConfig) -> None:
        with self._lock:
            self._configs[client_id] = config

    def get_state(self, client_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            window = self._windows.get(client_id)
            if not window:
                return None
            with window.lock:
                now = time.monotonic()
                cutoff = now - self._configs.get(client_id, self._default_config).window_seconds
                active = [t for t in window.timestamps if t >= cutoff]
                return {
                    "count": len(active),
                    "window_seconds": self._configs.get(client_id, self._default_config).window_seconds,
                    "window_max": self._configs.get(client_id, self._default_config).window_max,
                }

    def remove_client(self, client_id: str) -> None:
        with self._lock:
            self._windows.pop(client_id, None)
            self._configs.pop(client_id, None)


# ────────────────────────────────
# 3. Request Cache with TTL
# ────────────────────────────────

class RequestCache:
    """
    In-memory key-based cache with TTL expiration.
    Supports get, set, invalidate, and manual cleanup.
    """

    def __init__(self, default_ttl: float = 60.0, max_entries: int = 10_000) -> None:
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _cleanup_expired(self, now: float) -> None:
        expired = [k for k, v in self._store.items() if v.is_expired(now)]
        for k in expired:
            del self._store[k]

    def _evict_lru_if_needed(self) -> None:
        if len(self._store) >= self._max_entries:
            # Simple eviction: oldest by creation time
            oldest_key = min(self._store.keys(), key=lambda k: self._store[k].created_at)
            del self._store[oldest_key]
            self._evictions += 1

    def get(self, key: str) -> CacheReport:
        """Lookup entry by key. Returns hit, miss, or expired."""
        now = time.monotonic()
        with self._lock:
            self._cleanup_expired(now)
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return CacheReport(result=CacheResult.MISS, key=key)
            if entry.is_expired(now):
                del self._store[key]
                self._misses += 1
                return CacheReport(result=CacheResult.EXPIRED, key=key, age_seconds=now - entry.created_at)
            entry.access_count += 1
            self._hits += 1
            return CacheReport(
                result=CacheResult.HIT,
                key=key,
                value=entry.value,
                age_seconds=now - entry.created_at,
            )

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Store entry with optional custom TTL."""
        if ttl_seconds is None:
            ttl_seconds = self._default_ttl
        now = time.monotonic()
        with self._lock:
            self._cleanup_expired(now)
            self._evict_lru_if_needed()
            self._store[key] = CacheEntry(value=value, created_at=now, ttl_seconds=ttl_seconds)

    def invalidate(self, key: str) -> bool:
        """Remove entry by key. Returns True if existed."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Remove all keys containing pattern. Returns count removed."""
        removed = 0
        with self._lock:
            to_remove = [k for k in self._store if pattern in k]
            for k in to_remove:
                del self._store[k]
                removed += 1
        return removed

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "entries": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": round(hit_rate, 4),
            }

    def all_keys(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())


# ────────────────────────────────
# 4. Circuit Breaker Pattern
# ────────────────────────────────

class CircuitBreaker:
    """
    Circuit breaker with three states: CLOSED, OPEN, HALF_OPEN.
    - CLOSED: requests allowed
    - OPEN: requests rejected immediately
    - HALF_OPEN: one probe allowed; success → CLOSED, failure → OPEN
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 10.0,
        half_open_max_calls: int = 1,
        success_threshold_to_close: int = 2,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls
        self._success_threshold_to_close = success_threshold_to_close

        self._state = CircuitBreakerState()
        self._half_open_calls = 0
        self._lock = threading.Lock()

    def _can_attempt(self) -> bool:
        with self._lock:
            now = time.monotonic()
            state = self._state.state

            if state == CircuitState.CLOSED:
                return True
            if state == CircuitState.OPEN:
                if now - self._state.last_state_change >= self._recovery_timeout:
                    self._state.state = CircuitState.HALF_OPEN
                    self._state.last_state_change = now
                    self._half_open_calls = 0
                    self._state.success_count = 0
                    logger.info("Circuit breaker: OPEN → HALF_OPEN")
                    return True
                return False
            if state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self._half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            return True

    def call(self, fn: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute `fn` if circuit allows. If it fails, record failure.
        If success, record success. Returns result or raises CircuitBreakerError.
        """
        if not self._can_attempt():
            raise CircuitBreakerError("circuit open: request rejected")

        try:
            result = fn(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

    def _record_success(self) -> None:
        with self._lock:
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                if self._state.success_count >= self._success_threshold_to_close:
                    self._state.state = CircuitState.CLOSED
                    self._state.failure_count = 0
                    self._state.last_state_change = time.monotonic()
                    logger.info("Circuit breaker: HALF_OPEN → CLOSED")
            else:
                self._state.failure_count = 0

    def _record_failure(self) -> None:
        with self._lock:
            self._state.failure_count += 1
            self._state.last_failure_time = time.monotonic()
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.state = CircuitState.OPEN
                self._state.last_state_change = time.monotonic()
                logger.info("Circuit breaker: HALF_OPEN → OPEN")
            elif self._state.failure_count >= self._failure_threshold:
                if self._state.state != CircuitState.OPEN:
                    self._state.state = CircuitState.OPEN
                    self._state.last_state_change = time.monotonic()
                    logger.info("Circuit breaker: CLOSED → OPEN")

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state.state

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state": self._state.state.value,
                "failure_count": self._state.failure_count,
                "success_count": self._state.success_count,
                "last_failure_time": self._state.last_failure_time,
                "last_state_change": self._state.last_state_change,
            }

    def reset(self) -> None:
        with self._lock:
            self._state.state = CircuitState.CLOSED
            self._state.failure_count = 0
            self._state.success_count = 0
            self._state.last_state_change = 0.0
            self._half_open_calls = 0


class CircuitBreakerError(Exception):
    """Raised when the circuit breaker is OPEN and a request is attempted."""
    pass


# ────────────────────────────────
# 5. Distributed Rate Limiting Simulation
# ────────────────────────────────

class ConsistentHashRing:
    """
    Simple consistent hash ring for distributing clients across nodes.
    Used to simulate distributed rate limiting routing.
    """

    def __init__(self, nodes: List[str], replicas: int = 150) -> None:
        self._nodes = set(nodes)
        self._replicas = replicas
        self._ring: Dict[int, str] = {}
        self._sorted_keys: List[int] = []
        self._lock = threading.Lock()
        self._rebuild()

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def _rebuild(self) -> None:
        self._ring = {}
        for node in self._nodes:
            for i in range(self._replicas):
                h = self._hash(f"{node}:{i}")
                self._ring[h] = node
        self._sorted_keys = sorted(self._ring.keys())

    def add_node(self, node: str) -> None:
        with self._lock:
            self._nodes.add(node)
            self._rebuild()

    def remove_node(self, node: str) -> None:
        with self._lock:
            self._nodes.discard(node)
            self._rebuild()

    def get_node(self, key: str) -> Optional[str]:
        """Return the node responsible for `key`."""
        with self._lock:
            if not self._sorted_keys:
                return None
            h = self._hash(key)
            # Binary search for first hash >= h
            idx = self._bisect_right(self._sorted_keys, h)
            if idx == len(self._sorted_keys):
                idx = 0
            return self._ring[self._sorted_keys[idx]]

    @staticmethod
    def _bisect_right(a: List[int], x: int) -> int:
        lo, hi = 0, len(a)
        while lo < hi:
            mid = (lo + hi) // 2
            if a[mid] <= x:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def all_nodes(self) -> List[str]:
        with self._lock:
            return list(self._nodes)

    def ring_size(self) -> int:
        with self._lock:
            return len(self._ring)


class DistributedRateLimiter:
    """
    Simulates distributed rate limiting across multiple nodes.
    Uses a consistent hash ring to route clients to nodes, and maintains
    per-node rate limiters that can be queried/updated.
    """

    def __init__(self, nodes: List[str], default_config: RateLimitConfig) -> None:
        self._hash_ring = ConsistentHashRing(nodes)
        self._default_config = default_config
        self._node_limiters: Dict[str, TokenBucketRateLimiter] = {}
        self._lock = threading.Lock()
        for node in nodes:
            self._node_limiters[node] = TokenBucketRateLimiter(default_config)

    def allow(self, client_id: str, cost: float = 1.0) -> Tuple[RateLimitReport, str]:
        """Route client to responsible node and check rate limit."""
        node = self._hash_ring.get_node(client_id)
        if node is None:
            # Fallback: allow with warning
            return (
                RateLimitReport(
                    decision=RateLimitDecision.ALLOW,
                    client=client_id,
                    bucket_tokens=0.0,
                    window_count=0,
                    reason="no_node_available",
                ),
                "none",
            )
        limiter = self._node_limiters[node]
        report = limiter.allow(client_id, cost)
        return report, node

    def add_node(self, node: str) -> None:
        with self._lock:
            self._hash_ring.add_node(node)
            if node not in self._node_limiters:
                self._node_limiters[node] = TokenBucketRateLimiter(self._default_config)

    def remove_node(self, node: str) -> None:
        with self._lock:
            self._hash_ring.remove_node(node)
            self._node_limiters.pop(node, None)

    def get_node_for_client(self, client_id: str) -> Optional[str]:
        return self._hash_ring.get_node(client_id)

    def get_node_states(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                node: {
                    "clients": limiter.all_clients(),
                    "ring_hash_count": self._hash_ring.ring_size(),
                }
                for node, limiter in self._node_limiters.items()
            }

    def all_nodes(self) -> List[str]:
        return self._hash_ring.all_nodes()


# ────────────────────────────────
# 6. Unified Manager
# ────────────────────────────────

class RateLimitCacheManager:
    """
    Unified manager that ties together:
    - TokenBucketRateLimiter (per-client burst/refill)
    - SlidingWindowCounter (rolling window)
    - RequestCache (TTL in-memory cache)
    - CircuitBreaker (fault tolerance)
    - DistributedRateLimiter (multi-node simulation)
    """

    def __init__(
        self,
        default_config: Optional[RateLimitConfig] = None,
        default_ttl: float = 60.0,
        cache_max_entries: int = 10_000,
        nodes: Optional[List[str]] = None,
    ) -> None:
        if default_config is None:
            default_config = RateLimitConfig(
                burst=10, refill_rate=1.0, window_seconds=60, window_max=30
            )
        self._config = default_config

        self._token_bucket = TokenBucketRateLimiter(default_config)
        self._window_counter = SlidingWindowCounter(default_config)
        self._cache = RequestCache(default_ttl=default_ttl, max_entries=cache_max_entries)
        self._circuit = CircuitBreaker()
        self._distributed = DistributedRateLimiter(
            nodes or ["node-1", "node-2", "node-3"], default_config
        )

        self._request_log: Deque[Dict[str, Any]] = deque(maxlen=1000)
        self._lock = threading.Lock()

    # ── Public API ──

    def check_rate_limit(self, client_id: str, cost: float = 1.0) -> RateLimitReport:
        """Check token bucket AND sliding window. Both must allow."""
        bucket_report = self._token_bucket.allow(client_id, cost)
        if bucket_report.decision == RateLimitDecision.DENY:
            self._log_request(client_id, "denied", "bucket")
            return bucket_report

        window_report = self._window_counter.allow(client_id)
        if window_report.decision == RateLimitDecision.DENY:
            self._log_request(client_id, "denied", "window")
            return window_report

        self._log_request(client_id, "allowed", "both")
        return RateLimitReport(
            decision=RateLimitDecision.ALLOW,
            client=client_id,
            bucket_tokens=bucket_report.bucket_tokens,
            window_count=window_report.window_count,
            reason="both_passed",
        )

    def get_cached(self, key: str) -> CacheReport:
        """Check cache first. If miss, caller usually fetches and then `set_cache`."""
        return self._cache.get(key)

    def set_cache(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        self._cache.set(key, value, ttl_seconds)

    def invalidate_cache(self, key: str) -> bool:
        return self._cache.invalidate(key)

    def execute_with_circuit(self, fn: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:
        """Run function protected by circuit breaker."""
        return self._circuit.call(fn, *args, **kwargs)

    def distributed_allow(self, client_id: str, cost: float = 1.0) -> Tuple[RateLimitReport, str]:
        """Distributed rate limit check across simulated nodes."""
        return self._distributed.allow(client_id, cost)

    def get_node_for_client(self, client_id: str) -> Optional[str]:
        return self._distributed.get_node_for_client(client_id)

    # ── Configuration ──

    def set_client_config(self, client_id: str, config: RateLimitConfig) -> None:
        self._token_bucket.set_config(client_id, config)
        self._window_counter.set_config(client_id, config)

    def add_distributed_node(self, node: str) -> None:
        self._distributed.add_node(node)

    def remove_distributed_node(self, node: str) -> None:
        self._distributed.remove_node(node)

    # ── Status ──

    def get_status(self) -> Dict[str, Any]:
        return {
            "token_bucket_clients": len(self._token_bucket.all_clients()),
            "cache_stats": self._cache.stats(),
            "circuit_state": self._circuit.get_state(),
            "distributed_nodes": self._distributed.all_nodes(),
            "recent_requests": len(self._request_log),
        }

    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        return {
            "client_id": client_id,
            "bucket": self._token_bucket.get_state(client_id),
            "window": self._window_counter.get_state(client_id),
            "node": self._distributed.get_node_for_client(client_id),
        }

    def _log_request(self, client_id: str, result: str, component: str) -> None:
        with self._lock:
            self._request_log.append(
                {
                    "time": time.monotonic(),
                    "client": client_id,
                    "result": result,
                    "component": component,
                }
            )

    def get_recent_requests(self, n: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._request_log)[-n:]

    def reset(self) -> None:
        """Reset all stateful components."""
        self._token_bucket = TokenBucketRateLimiter(self._config)
        self._window_counter = SlidingWindowCounter(self._config)
        self._cache.clear()
        self._circuit.reset()
        with self._lock:
            self._request_log.clear()


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Rate Limiting & Cache Engine")
    print("ai/llm_rate_limiting_cache_native.py")
    print("=" * 60)

    config = RateLimitConfig(
        burst=5, refill_rate=2.0, window_seconds=10, window_max=8
    )
    manager = RateLimitCacheManager(default_config=config, default_ttl=5.0, nodes=["node-1", "node-2", "node-3"])

    # 1. Token Bucket Demo
    print("\n[1] Token Bucket Rate Limiter")
    client_a = "client-alpha"
    for i in range(8):
        r = manager.check_rate_limit(client_a, cost=1.0)
        print(f"  Request {i+1}: {r.decision.value} (tokens={r.bucket_tokens:.1f}, window={r.window_count}, reason={r.reason})")
    # Wait for refill
    print("  -- sleeping 2s for refill --")
    time.sleep(2.0)
    r = manager.check_rate_limit(client_a, cost=1.0)
    print(f"  After sleep: {r.decision.value} (tokens={r.bucket_tokens:.1f})")

    # 2. Sliding Window Demo
    print("\n[2] Sliding Window Counter")
    client_b = "client-beta"
    for i in range(10):
        r = manager.check_rate_limit(client_b)
        print(f"  Request {i+1}: {r.decision.value} (window={r.window_count})")

    # 3. Cache Demo
    print("\n[3] Request Cache with TTL")
    manager.set_cache("key-1", {"data": "hello"}, ttl_seconds=2.0)
    print(f"  Set key-1 → hello")
    r1 = manager.get_cached("key-1")
    print(f"  Get key-1: {r1.result.value}, value={r1.value}")
    time.sleep(2.5)
    r2 = manager.get_cached("key-1")
    print(f"  Get key-1 after 2.5s: {r2.result.value}")

    # 4. Circuit Breaker Demo
    print("\n[4] Circuit Breaker")
    failing_fn = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    for i in range(7):
        try:
            manager.execute_with_circuit(failing_fn)
        except (CircuitBreakerError, RuntimeError) as e:
            print(f"  Call {i+1}: {type(e).__name__}: {e}")
    print(f"  Circuit state: {manager._circuit.state.value}")
    # Success after timeout
    print("  -- sleeping 10.5s for recovery --")
    time.sleep(10.5)
    success_fn = lambda: "success"
    try:
        result = manager.execute_with_circuit(success_fn)
        print(f"  Probe call: {result}")
    except Exception as e:
        print(f"  Probe call failed: {e}")
    print(f"  Circuit state after probe: {manager._circuit.state.value}")
    # Close it fully
    for i in range(2):
        result = manager.execute_with_circuit(success_fn)
        print(f"  Success call {i+1}: {result}")
    print(f"  Circuit state final: {manager._circuit.state.value}")

    # 5. Distributed Rate Limiting Demo
    print("\n[5] Distributed Rate Limiting (Consistent Hash)")
    clients = [f"user-{i:03d}" for i in range(12)]
    for c in clients:
        report, node = manager.distributed_allow(c, cost=1.0)
        print(f"  {c} → {node}: {report.decision.value} (tokens={report.bucket_tokens:.1f})")
    print(f"  Node states: {manager._distributed.get_node_states()}")

    # 6. Status
    print("\n[6] Manager Status")
    status = manager.get_status()
    print(f"  {json.dumps(status, indent=4, default=str)}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
