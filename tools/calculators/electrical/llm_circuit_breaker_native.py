"""Circuit Breaker Pattern — fault tolerance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Callable, Any, Optional, List
from enum import Enum, auto
import time

class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0, half_open_max: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = 0.0
        self.half_open_attempts = 0
        self.history: List[Dict] = []

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_attempts = 0
            else:
                raise Exception("Circuit breaker is OPEN")
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_attempts >= self.half_open_max:
                raise Exception("Circuit breaker half-open max attempts reached")
            self.half_open_attempts += 1
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.half_open_max:
                self.state = CircuitState.CLOSED
                self.successes = 0
                self.half_open_attempts = 0
        self.history.append({"state": self.state.name, "result": "success", "time": time.time()})

    def _on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_attempts = 0
        elif self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
        self.history.append({"state": self.state.name, "result": "failure", "time": time.time()})

    def stats(self) -> Dict:
        return {"state": self.state.name, "failures": self.failures, "successes": self.successes, "last_failure": self.last_failure_time}

def run():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    def risky():
        raise ValueError("fail")
    for i in range(5):
        try:
            cb.call(risky)
        except Exception as e:
            print(f"Call {i}: {e}")
    print(cb.stats())

if __name__ == "__main__":
    run()
