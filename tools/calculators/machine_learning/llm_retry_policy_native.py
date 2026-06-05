"""Retry Policy — exponential backoff, jitter, circuit integration, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, List, Dict
from enum import Enum, auto
import time
import random
import math

class BackoffType(Enum):
    EXPONENTIAL = auto()
    LINEAR = auto()
    FIXED = auto()

class RetryPolicy:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, backoff: BackoffType = BackoffType.EXPONENTIAL, jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff = backoff
        self.jitter = jitter
        self.attempts: List[Dict] = []

    def _calculate_delay(self, attempt: int) -> float:
        if self.backoff == BackoffType.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempt)
        elif self.backoff == BackoffType.LINEAR:
            delay = self.base_delay * (attempt + 1)
        else:
            delay = self.base_delay
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay *= random.uniform(0.5, 1.5)
        return delay

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self.attempts.append({"attempt": attempt, "success": True, "delay": 0})
                return result
            except Exception as e:
                last_exception = e
                self.attempts.append({"attempt": attempt, "success": False, "delay": self._calculate_delay(attempt) if attempt < self.max_retries else 0})
                if attempt < self.max_retries:
                    time.sleep(self._calculate_delay(attempt))
        raise last_exception

    def stats(self) -> Dict:
        successes = sum(1 for a in self.attempts if a["success"])
        failures = sum(1 for a in self.attempts if not a["success"])
        return {"max_retries": self.max_retries, "attempts": len(self.attempts), "successes": successes, "failures": failures}

def run():
    policy = RetryPolicy(max_retries=3, base_delay=0.1, jitter=False)
    counter = [0]
    def flaky():
        counter[0] += 1
        if counter[0] < 3:
            raise ValueError("fail")
        return "success"
    result = policy.execute(flaky)
    print(result, counter[0])
    print(policy.stats())

if __name__ == "__main__":
    run()
