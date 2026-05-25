#!/usr/bin/env python3
"""
kernel/rate_limiter_native.py
=============================
Layer 0 — Rate Limiter (Token Bucket)

Provides:
  - Token bucket rate limiting per key (peer, user, endpoint)
  - Sliding window counter as alternative
  - Per-endpoint and global limits
  - Burst capacity with refill rate
  - Thread-safe implementation
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class RateLimitConfig:
    capacity: float = 10.0        # Maximum burst
    refill_rate: float = 1.0      # Tokens per second
    key: str = "default"


class TokenBucket:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, capacity: float, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def acquire(self, tokens: float = 1.0) -> Tuple[bool, float]:
        """Try to acquire tokens. Returns (success, wait_time)."""
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return (True, 0.0)
            deficit = tokens - self.tokens
            wait = deficit / self.refill_rate if self.refill_rate > 0 else float("inf")
            return (False, wait)

    def get_state(self) -> Dict[str, float]:
        with self._lock:
            self._refill()
            return {
                "tokens": self.tokens,
                "capacity": self.capacity,
                "refill_rate": self.refill_rate,
            }


class SlidingWindowCounter:
    """Sliding window rate limiter using timestamp ring buffer."""

    def __init__(self, window_sec: float = 60.0, max_requests: int = 100) -> None:
        self.window_sec = window_sec
        self.max_requests = max_requests
        self._requests: list[float] = []
        self._lock = threading.Lock()

    def _prune(self) -> None:
        cutoff = time.time() - self.window_sec
        self._requests = [t for t in self._requests if t > cutoff]

    def allow(self) -> Tuple[bool, int]:
        """Returns (allowed, remaining_quota)."""
        with self._lock:
            self._prune()
            if len(self._requests) < self.max_requests:
                self._requests.append(time.time())
                return (True, self.max_requests - len(self._requests))
            return (False, 0)

    def get_state(self) -> Dict[str, any]:
        with self._lock:
            self._prune()
            return {
                "requests_in_window": len(self._requests),
                "max_requests": self.max_requests,
                "window_sec": self.window_sec,
            }


class RateLimiterRegistry:
    """Global rate limiter registry for all endpoints and peers."""

    def __init__(self) -> None:
        self._buckets: Dict[str, TokenBucket] = {}
        self._windows: Dict[str, SlidingWindowCounter] = {}
        self._lock = threading.Lock()

    def get_bucket(self, key: str, capacity: float = 10.0,
                   refill_rate: float = 1.0) -> TokenBucket:
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(capacity, refill_rate)
            return self._buckets[key]

    def get_window(self, key: str, window_sec: float = 60.0,
                   max_requests: int = 100) -> SlidingWindowCounter:
        with self._lock:
            if key not in self._windows:
                self._windows[key] = SlidingWindowCounter(window_sec, max_requests)
            return self._windows[key]

    def check(self, key: str, tokens: float = 1.0,
              capacity: float = 10.0, refill_rate: float = 1.0) -> Tuple[bool, float]:
        """Quick check if request is allowed."""
        bucket = self.get_bucket(key, capacity, refill_rate)
        return bucket.acquire(tokens)

    def reset(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)
            self._windows.pop(key, None)


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  RATE LIMITER")
    print("=" * 60)
    bucket = TokenBucket(capacity=5, refill_rate=2)
    for i in range(8):
        ok, wait = bucket.acquire()
        status = "ALLOWED" if ok else f"BLOCKED (wait {wait:.1f}s)"
        print(f"  Request {i+1}: {status}")
    print(f"State: {bucket.get_state()}")
    print("=" * 60)


if __name__ == "__main__":
    demo()
