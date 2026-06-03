"""LLM Rate Limiter — Native Python (stdlib only)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class RateLimitStrategy(Enum):
    TOKEN_BUCKET = auto()
    FIXED_WINDOW = auto()
    SLIDING_WINDOW = auto()

@dataclass
class RateLimitConfig:
    key: str
    max_requests: int
    window_seconds: float
    strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW

class RateLimiter:
    def __init__(self) -> None:
        self._configs: Dict[str, RateLimitConfig] = {}
        self._requests: Dict[str, List[float]] = {}

    def set_config(self, config: RateLimitConfig) -> None:
        self._configs[config.key] = config
        self._requests[config.key] = []

    def allow(self, key: str) -> bool:
        config = self._configs.get(key)
        if not config:
            return True
        now = time.time()
        requests = self._requests.get(key, [])
        requests = [t for t in requests if now - t < config.window_seconds]
        self._requests[key] = requests
        if len(requests) < config.max_requests:
            requests.append(now)
            return True
        return False

    def get_remaining(self, key: str) -> int:
        config = self._configs.get(key)
        if not config:
            return -1
        now = time.time()
        requests = [t for t in self._requests.get(key, []) if now - t < config.window_seconds]
        return max(0, config.max_requests - len(requests))

    def get_stats(self) -> Dict[str, Any]:
        return {"keys": len(self._configs), "total_requests": sum(len(v) for v in self._requests.values())}

def run() -> None:
    print("Rate Limiter test")
    e = RateLimiter()
    e.set_config(RateLimitConfig("user1", 3, 60.0, RateLimitStrategy.FIXED_WINDOW))
    for i in range(5):
        allowed = e.allow("user1")
        print("  Request " + str(i + 1) + ": " + ("allowed" if allowed else "blocked") + " (remaining: " + str(e.get_remaining("user1")) + ")")
    print("  Stats: " + str(e.get_stats()))
    print("Rate Limiter test complete.")

if __name__ == "__main__":
    run()
