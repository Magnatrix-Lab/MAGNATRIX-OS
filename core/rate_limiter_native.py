#!/usr/bin/env python3
"""
Rate Limiter for MAGNATRIX-OS
Per-user, per-IP, and per-token throttling with sliding window,
leaky bucket, and circuit breaker patterns.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class LimitStrategy(enum.Enum):
    SLIDING_WINDOW = "sliding_window"
    LEAKY_BUCKET = "leaky_bucket"
    FIXED_WINDOW = "fixed_window"


class CircuitState(enum.Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # rejecting requests
    HALF_OPEN = "half_open"  # testing if service recovered


@dataclasses.dataclass
class RateLimitRule:
    """Defines a rate limit rule."""
    name: str
    max_requests: int
    window_seconds: float
    strategy: LimitStrategy = LimitStrategy.SLIDING_WINDOW
    burst_size: int = 0  # for leaky bucket
    cooldown_seconds: float = 0.0  # after breach


@dataclasses.dataclass
class RateLimitEntry:
    """Tracking entry for a single key."""
    key: str
    requests: List[float] = dataclasses.field(default_factory=list)
    blocked_until: float = 0.0
    total_allowed: int = 0
    total_rejected: int = 0

    def prune_old(self, window: float) -> None:
        now = time.time()
        self.requests = [t for t in self.requests if now - t < window]


@dataclasses.dataclass
class CircuitBreakerEntry:
    """Circuit breaker state for a single key."""
    key: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = dataclasses.field(default_factory=time.time)


class RateLimiter:
    """Multi-strategy rate limiter with circuit breaker support."""

    def __init__(self) -> None:
        self._rules: Dict[str, RateLimitRule] = {}
        self._entries: Dict[str, RateLimitEntry] = {}
        self._circuits: Dict[str, CircuitBreakerEntry] = {}
        self._lock = threading.Lock()
        self._global_allowed = 0
        self._global_rejected = 0

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: RateLimitRule) -> None:
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> bool:
        return self._rules.pop(name, None) is not None

    # ------------------------------------------------------------------
    # Rate limit check
    # ------------------------------------------------------------------

    def is_allowed(self, key: str, rule_name: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under given rule."""
        rule = self._rules.get(rule_name)
        if not rule:
            return True, {"rule": None}
        with self._lock:
            entry = self._entries.setdefault(key, RateLimitEntry(key=key))
            now = time.time()
            # Check cooldown
            if now < entry.blocked_until:
                entry.total_rejected += 1
                self._global_rejected += 1
                return False, {
                    "rule": rule_name,
                    "blocked_until": entry.blocked_until,
                    "retry_after": round(entry.blocked_until - now, 2),
                }
            # Apply strategy
            if rule.strategy == LimitStrategy.SLIDING_WINDOW:
                entry.prune_old(rule.window_seconds)
                if len(entry.requests) >= rule.max_requests:
                    entry.blocked_until = now + rule.cooldown_seconds
                    entry.total_rejected += 1
                    self._global_rejected += 1
                    return False, {
                        "rule": rule_name,
                        "window": rule.window_seconds,
                        "current": len(entry.requests),
                        "limit": rule.max_requests,
                        "retry_after": rule.cooldown_seconds,
                    }
                entry.requests.append(now)
                entry.total_allowed += 1
                self._global_allowed += 1
                return True, {
                    "rule": rule_name,
                    "remaining": rule.max_requests - len(entry.requests),
                    "reset": round(now + rule.window_seconds, 2),
                }
            elif rule.strategy == LimitStrategy.LEAKY_BUCKET:
                # Simulate bucket: allow bursts up to burst_size within window
                entry.prune_old(rule.window_seconds)
                if len(entry.requests) >= rule.max_requests + rule.burst_size:
                    entry.total_rejected += 1
                    self._global_rejected += 1
                    return False, {
                        "rule": rule_name,
                        "bucket_full": True,
                        "retry_after": rule.window_seconds,
                    }
                entry.requests.append(now)
                entry.total_allowed += 1
                self._global_allowed += 1
                return True, {
                    "rule": rule_name,
                    "remaining": rule.max_requests + rule.burst_size - len(entry.requests),
                }
            else:
                # Fixed window
                window_start = now - (now % rule.window_seconds)
                window_requests = [t for t in entry.requests if t >= window_start]
                if len(window_requests) >= rule.max_requests:
                    entry.total_rejected += 1
                    self._global_rejected += 1
                    return False, {
                        "rule": rule_name,
                        "window_start": window_start,
                        "current": len(window_requests),
                        "limit": rule.max_requests,
                    }
                entry.requests.append(now)
                entry.total_allowed += 1
                self._global_allowed += 1
                return True, {
                    "rule": rule_name,
                    "remaining": rule.max_requests - len(window_requests),
                }

    # ------------------------------------------------------------------
    # Circuit breaker
    # ------------------------------------------------------------------

    def circuit_check(self, key: str, failure_threshold: int = 5, recovery_timeout: float = 30.0, half_open_max: int = 3) -> Tuple[bool, CircuitState]:
        """Check circuit breaker state. Returns (can_proceed, current_state)."""
        with self._lock:
            circuit = self._circuits.setdefault(key, CircuitBreakerEntry(key=key))
            now = time.time()
            if circuit.state == CircuitState.OPEN:
                if now - circuit.last_state_change > recovery_timeout:
                    circuit.state = CircuitState.HALF_OPEN
                    circuit.success_count = 0
                    circuit.last_state_change = now
                else:
                    return False, circuit.state
            if circuit.state == CircuitState.HALF_OPEN:
                if circuit.success_count >= half_open_max:
                    circuit.state = CircuitState.CLOSED
                    circuit.failure_count = 0
                    circuit.last_state_change = now
                    return True, circuit.state
            return True, circuit.state

    def report_success(self, key: str) -> None:
        with self._lock:
            circuit = self._circuits.get(key)
            if not circuit:
                return
            if circuit.state == CircuitState.HALF_OPEN:
                circuit.success_count += 1
            else:
                circuit.failure_count = max(0, circuit.failure_count - 1)

    def report_failure(self, key: str, failure_threshold: int = 5) -> None:
        with self._lock:
            circuit = self._circuits.setdefault(key, CircuitBreakerEntry(key=key))
            circuit.failure_count += 1
            circuit.last_failure_time = time.time()
            if circuit.failure_count >= failure_threshold:
                circuit.state = CircuitState.OPEN
                circuit.last_state_change = time.time()
                circuit.success_count = 0

    # ------------------------------------------------------------------
    # Decorator
    # ------------------------------------------------------------------

    def limit(self, key_func: Callable[..., str], rule_name: str):
        """Decorator to apply rate limiting to a function."""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> Any:
                key = key_func(*args, **kwargs)
                allowed, info = self.is_allowed(key, rule_name)
                if not allowed:
                    raise RateLimitExceeded(f"Rate limit exceeded: {info}")
                result = func(*args, **kwargs)
                self.report_success(key)
                return result
            return wrapper
        return decorator

    # ------------------------------------------------------------------
    # Query & cleanup
    # ------------------------------------------------------------------

    def get_entry(self, key: str) -> Optional[RateLimitEntry]:
        return self._entries.get(key)

    def get_circuit(self, key: str) -> Optional[CircuitBreakerEntry]:
        return self._circuits.get(key)

    def reset(self, key: str) -> bool:
        with self._lock:
            self._entries.pop(key, None)
            self._circuits.pop(key, None)
            return True

    def reset_all(self) -> None:
        with self._lock:
            self._entries.clear()
            self._circuits.clear()
            self._global_allowed = 0
            self._global_rejected = 0

    def prune_stale(self, max_age_seconds: float = 3600) -> int:
        """Remove entries with no recent activity."""
        now = time.time()
        with self._lock:
            stale = [k for k, e in self._entries.items() if e.requests and now - max(e.requests) > max_age_seconds]
            for k in stale:
                del self._entries[k]
            return len(stale)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "rules": len(self._rules),
                "tracked_keys": len(self._entries),
                "circuits": len(self._circuits),
                "global_allowed": self._global_allowed,
                "global_rejected": self._global_rejected,
                "circuit_states": {
                    "closed": sum(1 for c in self._circuits.values() if c.state == CircuitState.CLOSED),
                    "open": sum(1 for c in self._circuits.values() if c.state == CircuitState.OPEN),
                    "half_open": sum(1 for c in self._circuits.values() if c.state == CircuitState.HALF_OPEN),
                },
            }


class RateLimitExceeded(Exception):
    """Raised when a rate limit is breached."""
    pass


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    rl = RateLimiter()
    print("=== Rate Limiter Demo ===\n")
    # Add rules
    rl.add_rule(RateLimitRule("api_per_user", max_requests=5, window_seconds=10, strategy=LimitStrategy.SLIDING_WINDOW, cooldown_seconds=2))
    rl.add_rule(RateLimitRule("login_per_ip", max_requests=3, window_seconds=60, strategy=LimitStrategy.FIXED_WINDOW))
    rl.add_rule(RateLimitRule("burst_api", max_requests=10, window_seconds=5, strategy=LimitStrategy.LEAKY_BUCKET, burst_size=5))
    # Test sliding window
    print("Sliding window test (5 req/10s):")
    for i in range(7):
        allowed, info = rl.is_allowed("user_123", "api_per_user")
        print(f"  Request {i+1}: {'OK' if allowed else 'BLOCKED'} (remaining={info.get('remaining', 'N/A')})")
    # Wait for cooldown
    time.sleep(2.5)
    allowed, info = rl.is_allowed("user_123", "api_per_user")
    print(f"  After cooldown: {'OK' if allowed else 'BLOCKED'} (remaining={info.get('remaining', 'N/A')})")
    # Circuit breaker test
    print(f"\nCircuit breaker test:")
    for i in range(7):
        ok, state = rl.circuit_check("service_a", failure_threshold=3)
        if i < 3:
            rl.report_success("service_a")
            print(f"  Call {i+1}: {state.value} (reported success)")
        else:
            rl.report_failure("service_a", failure_threshold=3)
            print(f"  Call {i+1}: {state.value} (reported failure)")
    print(f"\nStats: {rl.stats()}")


if __name__ == "__main__":
    _demo()
