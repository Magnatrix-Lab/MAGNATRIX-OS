"""
llm_quota_manager_native.py
MAGNATRIX-OS Quota Manager Engine
Native Python, stdlib only.
Provides per-user, per-model, and per-operation quota enforcement with windowed limits and burst handling.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class QuotaWindow(Enum):
    SECOND = 1
    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    MONTH = 2592000


@dataclass
class Quota:
    resource: str
    limit: float
    window: QuotaWindow
    current: float = 0.0
    window_start: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {"resource": self.resource, "limit": self.limit, "window": self.window.value, "current": self.current}

    def reset_if_needed(self) -> None:
        now = time.time()
        if now - self.window_start >= self.window.value:
            self.current = 0.0
            self.window_start = now

    def consume(self, amount: float) -> bool:
        self.reset_if_needed()
        if self.current + amount > self.limit:
            return False
        self.current += amount
        return True

    def remaining(self) -> float:
        self.reset_if_needed()
        return max(0.0, self.limit - self.current)


class QuotaManagerEngine:
    """Quota management with multi-window enforcement."""

    def __init__(self) -> None:
        self._quotas: Dict[str, Dict[str, Quota]] = {}  # user_id -> {resource: quota}
        self._handlers: List[Callable[[str, str, float], None]] = []

    def set_quota(self, user_id: str, resource: str, limit: float, window: QuotaWindow) -> Quota:
        if user_id not in self._quotas:
            self._quotas[user_id] = {}
        quota = Quota(resource=resource, limit=limit, window=window)
        self._quotas[user_id][resource] = quota
        return quota

    def check(self, user_id: str, resource: str, amount: float = 1.0) -> bool:
        user_quotas = self._quotas.get(user_id, {})
        quota = user_quotas.get(resource)
        if not quota:
            return True  # No quota = unlimited
        return quota.consume(amount)

    def consume(self, user_id: str, resource: str, amount: float = 1.0) -> bool:
        ok = self.check(user_id, resource, amount)
        if not ok:
            for handler in self._handlers:
                handler(user_id, resource, amount)
        return ok

    def get_remaining(self, user_id: str, resource: str) -> float:
        user_quotas = self._quotas.get(user_id, {})
        quota = user_quotas.get(resource)
        return quota.remaining() if quota else float('inf')

    def add_handler(self, handler: Callable[[str, str, float], None]) -> None:
        self._handlers.append(handler)

    def get_user_quotas(self, user_id: str) -> Dict[str, Quota]:
        return dict(self._quotas.get(user_id, {}))

    def get_stats(self) -> Dict[str, Any]:
        total_quotas = sum(len(q) for q in self._quotas.values())
        return {"users": len(self._quotas), "total_quotas": total_quotas}


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Quota Manager Engine")
    print("=" * 60)

    engine = QuotaManagerEngine()

    def quota_alert(user_id: str, resource: str, amount: float) -> None:
        print(f"  [QUOTA] {user_id} exceeded {resource} (requested {amount})")

    engine.add_handler(quota_alert)

    print("\n--- Set quotas ---")
    engine.set_quota("user_1", "requests_per_minute", 10, QuotaWindow.MINUTE)
    engine.set_quota("user_1", "tokens_per_day", 100000, QuotaWindow.DAY)
    engine.set_quota("user_2", "requests_per_minute", 5, QuotaWindow.MINUTE)

    print("\n--- Consume requests ---")
    for i in range(12):
        ok = engine.consume("user_1", "requests_per_minute", 1)
        print(f"  user_1 request {i+1}: {'allowed' if ok else 'DENIED'}")

    print("\n--- Remaining ---")
    print(f"  user_1 requests: {engine.get_remaining('user_1', 'requests_per_minute')}")
    print(f"  user_1 tokens: {engine.get_remaining('user_1', 'tokens_per_day')}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nQuota Manager test complete.")


if __name__ == "__main__":
    run()
