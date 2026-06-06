#!/usr/bin/env python3
"""
Cost Tracker for MAGNATRIX-OS
API usage cost tracking, per model/user/request, budget alerts.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional


class CostEntry:
    """Single cost entry."""

    def __init__(self, model: str, user_id: str, tokens_in: int, tokens_out: int, cost: float, timestamp: float) -> None:
        self.model = model
        self.user_id = user_id
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost = cost
        self.timestamp = timestamp


class CostTracker:
    """API usage cost tracking."""

    def __init__(self, storage_path: str = './costs.json') -> None:
        self._storage_path = storage_path
        self._entries: List[CostEntry] = []
        self._rates: Dict[str, float] = {
            'llama3.2:3b': 0.0,  # Local = free
            'qwen2.5:7b': 0.0,
            'gpt-4': 0.03,
            'gpt-3.5-turbo': 0.002,
        }
        self._budgets: Dict[str, float] = {}
        self._alerts: List[Dict[str, Any]] = []

    def set_rate(self, model: str, rate_per_1k_tokens: float) -> None:
        self._rates[model] = rate_per_1k_tokens

    def set_budget(self, user_id: str, budget: float) -> None:
        self._budgets[user_id] = budget

    def record(self, model: str, user_id: str, tokens_in: int, tokens_out: int) -> float:
        rate = self._rates.get(model, 0.0)
        cost = (tokens_in + tokens_out) / 1000 * rate

        entry = CostEntry(model, user_id, tokens_in, tokens_out, cost, time.time())
        self._entries.append(entry)

        # Check budget
        if user_id in self._budgets:
            total = self.get_user_cost(user_id, time.time() - 86400)
            if total >= self._budgets[user_id] * 0.9:
                self._alerts.append({
                    'user_id': user_id,
                    'message': f'Budget {self._budgets[user_id]} almost exceeded ({total:.2f})',
                    'timestamp': time.time(),
                })

        return cost

    def get_user_cost(self, user_id: str, since: float = 0) -> float:
        return sum(e.cost for e in self._entries if e.user_id == user_id and e.timestamp >= since)

    def get_model_cost(self, model: str, since: float = 0) -> float:
        return sum(e.cost for e in self._entries if e.model == model and e.timestamp >= since)

    def get_daily_summary(self) -> Dict[str, Any]:
        today = time.time() - (time.time() % 86400)
        entries = [e for e in self._entries if e.timestamp >= today]
        return {
            'total_cost': sum(e.cost for e in entries),
            'total_tokens': sum(e.tokens_in + e.tokens_out for e in entries),
            'requests': len(entries),
            'by_model': self._group_by_model(entries),
        }

    def _group_by_model(self, entries: List[CostEntry]) -> Dict[str, Dict[str, float]]:
        result: Dict[str, Dict[str, float]] = {}
        for e in entries:
            if e.model not in result:
                result[e.model] = {'cost': 0.0, 'tokens': 0}
            result[e.model]['cost'] += e.cost
            result[e.model]['tokens'] += e.tokens_in + e.tokens_out
        return result

    def get_alerts(self) -> List[Dict[str, Any]]:
        return self._alerts[-10:]

    def stats(self) -> Dict[str, Any]:
        return {
            'total_entries': len(self._entries),
            'total_cost': sum(e.cost for e in self._entries),
            'alerts': len(self._alerts),
        }


def _demo() -> None:
    print("=== Cost Tracker Demo ===\n")

    tracker = CostTracker()
    tracker.set_budget('user_1', 10.0)
    tracker.set_rate('gpt-4', 0.03)

    # Record usage
    c1 = tracker.record('gpt-4', 'user_1', 1000, 500)
    c2 = tracker.record('gpt-4', 'user_1', 2000, 1000)
    c3 = tracker.record('llama3.2:3b', 'user_1', 5000, 2000)  # Free

    print(f"Cost 1: ${c1:.4f}")
    print(f"Cost 2: ${c2:.4f}")
    print(f"Cost 3: ${c3:.4f} (local model)")
    print(f"User total: ${tracker.get_user_cost('user_1'):.4f}")
    print(f"Daily summary: {tracker.get_daily_summary()}")
    print(f"Alerts: {len(tracker.get_alerts())}")

    print("\n=== Cost Tracker Demo Complete ===")


if __name__ == '__main__':
    _demo()
