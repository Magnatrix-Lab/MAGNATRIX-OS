"""
llm_circuit_breaker_native.py
MAGNATRIX-OS Circuit Breaker Engine
Native Python, stdlib only.
Provides circuit breaker pattern for resilient LLM API calls with CLOSED, OPEN, and HALF_OPEN states.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerEngine:
    """
    Circuit breaker for resilient API calls.
    CLOSED: normal operation
    OPEN: failing fast, rejecting requests
    HALF_OPEN: allowing probe requests after cooldown
    """

    def __init__(
        self, name: str, failure_threshold: int = 5,
        recovery_timeout: float = 30.0, half_open_max_calls: int = 3,
        success_threshold: int = 2
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []
        self._total_requests = 0
        self._total_failures = 0
        self._total_successes = 0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._maybe_transition()
            return self._state

    def _maybe_transition(self) -> None:
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and (time.time() - self._last_failure_time) >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._success_count = 0
        elif self._state == CircuitState.HALF_OPEN:
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._half_open_calls = 0
            elif self._half_open_calls >= self.half_open_max_calls and self._success_count < self.success_threshold:
                self._state = CircuitState.OPEN
                self._last_failure_time = time.time()
                self._half_open_calls = 0

    def call(self, fn: Callable, *args, fallback: Optional[Callable] = None, **kwargs) -> Any:
        with self._lock:
            self._maybe_transition()
            self._total_requests += 1

            if self._state == CircuitState.OPEN:
                self._history.append({"state": "OPEN", "time": time.time(), "action": "rejected"})
                if fallback:
                    return fallback(*args, **kwargs)
                raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    self._history.append({"state": "HALF_OPEN", "time": time.time(), "action": "rejected"})
                    if fallback:
                        return fallback(*args, **kwargs)
                    raise CircuitBreakerOpen(f"Circuit {self.name} HALF_OPEN limit reached")
                self._half_open_calls += 1

            # CLOSED or allowed HALF_OPEN call
        try:
            result = fn(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

    def _record_success(self) -> None:
        with self._lock:
            self._total_successes += 1
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._maybe_transition()
            else:
                self._failure_count = max(0, self._failure_count - 1)
            self._history.append({"state": self._state.value, "time": time.time(), "action": "success"})

    def _record_failure(self) -> None:
        with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
            self._history.append({"state": self._state.value, "time": time.time(), "action": "failure"})

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._maybe_transition()
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "total_requests": self._total_requests,
                "total_successes": self._total_successes,
                "total_failures": self._total_failures,
                "last_failure_time": self._last_failure_time,
                "failure_rate": self._total_failures / max(self._total_requests, 1),
            }

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._history[-limit:]


class CircuitBreakerOpen(Exception):
    pass


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Circuit Breaker Engine")
    print("=" * 60)

    cb = CircuitBreakerEngine(
        name="llm_api", failure_threshold=3,
        recovery_timeout=2.0, half_open_max_calls=2, success_threshold=1
    )

    def failing_call() -> str:
        raise RuntimeError("LLM API timeout")

    def success_call() -> str:
        return "LLM response OK"

    print("\n--- CLOSED state, failures accumulate ---")
    for i in range(4):
        try:
            cb.call(failing_call)
        except CircuitBreakerOpen:
            print(f"  Call {i+1}: Circuit OPEN (fast fail)")
        except RuntimeError:
            print(f"  Call {i+1}: RuntimeError (passing through)")
        print(f"    State: {cb.state.value}, failures: {cb.get_stats()['failure_count']}")

    print("\n--- Wait for recovery timeout ---")
    time.sleep(2.5)
    print(f"  State after sleep: {cb.state.value}")

    print("\n--- HALF_OPEN, probe succeeds ---")
    try:
        result = cb.call(success_call)
        print(f"  Result: {result}")
    except Exception as e:
        print(f"  Error: {e}")
    print(f"  State: {cb.state.value}")

    print("\n--- Stats ---")
    stats = cb.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\nCircuit Breaker test complete.")


if __name__ == "__main__":
    run()
