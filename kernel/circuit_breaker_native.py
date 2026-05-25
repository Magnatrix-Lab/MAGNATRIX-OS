#!/usr/bin/env python3
"""
kernel/circuit_breaker_native.py
================================
Layer 0 — Circuit Breaker & Bulkhead

Provides:
  - Circuit breaker state machine (CLOSED → OPEN → HALF_OPEN)
  - Per-service failure tracking
  - Automatic recovery detection
  - Bulkhead (semaphore-based concurrency limiting)
  - Fallback handler support
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Optional, Any, Tuple


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failure threshold reached, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    success_threshold: int = 2


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(self, name: str, config: CircuitConfig) -> None:
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._half_open_calls = 0
        self._last_failure_time = 0.0
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], T], fallback: Optional[Callable[[], T]] = None) -> T:
        """Execute fn with circuit breaker protection."""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self._last_failure_time > self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._successes = 0
                else:
                    if fallback:
                        return fallback()
                    raise CircuitBreakerOpen(f"Circuit '{self.name}' is OPEN")
            
            if self.state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    if fallback:
                        return fallback()
                    raise CircuitBreakerOpen(f"Circuit '{self.name}' HALF_OPEN limit reached")
                self._half_open_calls += 1

        try:
            result = fn()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self._successes += 1
                if self._successes >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self._failures = 0
                    self._successes = 0
            elif self.state == CircuitState.CLOSED:
                self._failures = max(0, self._failures - 1)

    def _on_failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
            elif self._failures >= self.config.failure_threshold:
                self.state = CircuitState.OPEN

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self.state == CircuitState.OPEN

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failures": self._failures,
                "successes": self._successes,
                "last_failure": self._last_failure_time,
            }


class CircuitBreakerOpen(Exception):
    pass


class Bulkhead:
    """Semaphore-based concurrency limiter."""

    def __init__(self, max_concurrent: int, max_queue: int = 0) -> None:
        self._semaphore = threading.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._max_queue = max_queue
        self._active = 0
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], T]) -> T:
        acquired = self._semaphore.acquire(timeout=5.0 if self._max_queue > 0 else 0.0)
        if not acquired:
            raise BulkheadFull("Bulkhead capacity exceeded")
        try:
            with self._lock:
                self._active += 1
            return fn()
        finally:
            with self._lock:
                self._active -= 1
            self._semaphore.release()

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "max": self._max_concurrent,
                "active": self._active,
                "available": self._max_concurrent - self._active,
            }


class BulkheadFull(Exception):
    pass


class CircuitBreakerRegistry:
    """Global registry of circuit breakers for all external services."""

    def __init__(self) -> None:
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get(self, name: str, config: Optional[CircuitConfig] = None) -> CircuitBreaker:
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config or CircuitConfig())
            return self._breakers[name]

    def reset(self, name: str) -> None:
        with self._lock:
            self._breakers.pop(name, None)

    def stats(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {name: cb.get_state() for name, cb in self._breakers.items()}


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  CIRCUIT BREAKER")
    print("=" * 60)
    cb = CircuitBreaker("test-service", CircuitConfig(failure_threshold=3, recovery_timeout=1.0))
    
    # Simulate failures
    for i in range(5):
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except Exception as e:
            print(f"  Call {i+1}: {type(e).__name__}: {e}")
    
    print(f"State after failures: {cb.get_state()}")
    
    # Wait for recovery window
    time.sleep(1.1)
    
    # Success in half-open
    try:
        result = cb.call(lambda: "success")
        print(f"  Recovery call: {result}")
    except Exception as e:
        print(f"  Recovery call failed: {e}")
    
    print(f"Final state: {cb.get_state()}")
    print("=" * 60)


if __name__ == "__main__":
    demo()
