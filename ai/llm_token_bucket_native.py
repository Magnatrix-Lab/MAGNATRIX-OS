"""
llm_token_bucket_native.py
MAGNATRIX-OS Token Bucket Rate Limiter
Native Python, stdlib only.
Provides token bucket rate limiting with per-key quotas, burst support, and refill scheduling.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class Bucket:
    key: str
    capacity: float
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key, "capacity": self.capacity, "tokens": round(self.tokens, 2),
            "refill_rate": self.refill_rate, "last_refill": self.last_refill,
        }


class TokenBucketEngine:
    """
    Token bucket rate limiter with per-key tracking and burst support.
    """

    def __init__(self, default_capacity: float = 100.0, default_refill_rate: float = 10.0) -> None:
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self._buckets: Dict[str, Bucket] = {}
        self._lock = threading.Lock()
        self._total_requests = 0
        self._total_allowed = 0
        self._total_rejected = 0
        self._wait_requests = 0

    def _get_or_create(self, key: str, capacity: Optional[float] = None, refill_rate: Optional[float] = None) -> Bucket:
        if key not in self._buckets:
            cap = capacity if capacity is not None else self.default_capacity
            rate = refill_rate if refill_rate is not None else self.default_refill_rate
            self._buckets[key] = Bucket(key=key, capacity=cap, tokens=cap, refill_rate=rate, last_refill=time.time())
        return self._buckets[key]

    def _refill(self, bucket: Bucket) -> None:
        now = time.time()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(bucket.capacity, bucket.tokens + elapsed * bucket.refill_rate)
        bucket.last_refill = now

    def allow(self, key: str, tokens: float = 1.0, capacity: Optional[float] = None, refill_rate: Optional[float] = None) -> bool:
        with self._lock:
            self._total_requests += 1
            bucket = self._get_or_create(key, capacity, refill_rate)
            self._refill(bucket)
            if bucket.tokens >= tokens:
                bucket.tokens -= tokens
                self._total_allowed += 1
                return True
            self._total_rejected += 1
            return False

    def consume_or_wait(self, key: str, tokens: float = 1.0, timeout: float = 5.0, capacity: Optional[float] = None, refill_rate: Optional[float] = None) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                bucket = self._get_or_create(key, capacity, refill_rate)
                self._refill(bucket)
                if bucket.tokens >= tokens:
                    bucket.tokens -= tokens
                    self._total_allowed += 1
                    self._wait_requests += 1
                    return True
            time.sleep(0.05)
        return False

    def get_bucket(self, key: str) -> Optional[Bucket]:
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket:
                self._refill(bucket)
            return bucket

    def get_stats(self, key: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if key:
                b = self._buckets.get(key)
                if b:
                    self._refill(b)
                    return b.to_dict()
                return {}
            return {
                "total_requests": self._total_requests,
                "total_allowed": self._total_allowed,
                "total_rejected": self._total_rejected,
                "wait_requests": self._wait_requests,
                "rejection_rate": round(self._total_rejected / max(self._total_requests, 1), 4),
                "buckets": len(self._buckets),
            }

    def reset(self, key: str) -> bool:
        with self._lock:
            if key in self._buckets:
                b = self._buckets[key]
                b.tokens = b.capacity
                b.last_refill = time.time()
                return True
            return False

    def reset_all(self) -> None:
        with self._lock:
            for b in self._buckets.values():
                b.tokens = b.capacity
                b.last_refill = time.time()
            self._total_requests = 0
            self._total_allowed = 0
            self._total_rejected = 0
            self._wait_requests = 0

    def set_quota(self, key: str, capacity: float, refill_rate: float) -> None:
        with self._lock:
            bucket = self._get_or_create(key, capacity, refill_rate)
            bucket.capacity = capacity
            bucket.refill_rate = refill_rate
            bucket.tokens = min(bucket.tokens, capacity)

    def list_keys(self) -> list[str]:
        return list(self._buckets.keys())


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Token Bucket Rate Limiter")
    print("=" * 60)

    engine = TokenBucketEngine(default_capacity=10.0, default_refill_rate=2.0)

    print("\n--- Burst consumption ---")
    for i in range(15):
        ok = engine.allow("api_key_123", tokens=1.0)
        print(f"  Request {i+1}: {'allowed' if ok else 'REJECTED'}")

    print(f"\n  Bucket state: {engine.get_bucket('api_key_123').to_dict()}")

    print("\n--- Wait for refill ---")
    time.sleep(1.5)
    print(f"  After 1.5s: {engine.get_bucket('api_key_123').to_dict()}")

    print("\n--- Consume or wait ---")
    ok = engine.consume_or_wait("api_key_123", tokens=5.0, timeout=3.0)
    print(f"  Consumed 5 tokens with wait: {ok}")
    print(f"  Bucket state: {engine.get_bucket('api_key_123').to_dict()}")

    print("\n--- Custom quota ---")
    engine.set_quota("premium_user", capacity=100.0, refill_rate=20.0)
    for i in range(5):
        ok = engine.allow("premium_user", tokens=10.0)
        print(f"  Premium request {i+1}: {'allowed' if ok else 'REJECTED'}")

    print("\n--- Stats ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\nToken Bucket test complete.")


if __name__ == "__main__":
    run()
