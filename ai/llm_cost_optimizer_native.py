#!/usr/bin/env python3
"""
MAGNATRIX-OS — Cost Optimizer Engine
ai/llm_cost_optimizer_native.py

Features:
- Token cost estimation (input/output token pricing)
- Model selection by cost-effectiveness (cheapest for task)
- Budget tracking and alerts (spend tracking, threshold alerts)
- Caching simulation for cost reduction (cache hit = no cost)
- Cost report generation (per model, per user, per day)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cost_optimizer")


@dataclass
class ModelPricing:
    model_id: str
    input_price_per_1k: float  # USD per 1K input tokens
    output_price_per_1k: float  # USD per 1K output tokens


@dataclass
class UsageRecord:
    model_id: str
    input_tokens: int
    output_tokens: int
    timestamp: float
    user_id: str = ""
    cached: bool = False


class CostOptimizerEngine:
    """Cost tracking, estimation, and optimization."""

    def __init__(self, budget_limit: float = 100.0):
        self.budget_limit = budget_limit
        self._pricing: Dict[str, ModelPricing] = {}
        self._usage: List[UsageRecord] = []
        self._cache_hits = 0
        self._cache_misses = 0

    def set_pricing(self, pricing: ModelPricing) -> None:
        self._pricing[pricing.model_id] = pricing

    def estimate(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        p = self._pricing.get(model_id)
        if not p:
            return 0.0
        cost = (input_tokens / 1000 * p.input_price_per_1k) + (output_tokens / 1000 * p.output_price_per_1k)
        return round(cost, 6)

    def record(self, usage: UsageRecord) -> float:
        if usage.cached:
            self._cache_hits += 1
            cost = 0.0
        else:
            self._cache_misses += 1
            cost = self.estimate(usage.model_id, usage.input_tokens, usage.output_tokens)
        usage.cost = cost
        self._usage.append(usage)
        return cost

    def cheapest_for(self, input_tokens: int, output_tokens: int, candidates: List[str]) -> Optional[Tuple[str, float]]:
        """Find cheapest model for given token counts."""
        estimates = []
        for mid in candidates:
            cost = self.estimate(mid, input_tokens, output_tokens)
            estimates.append((cost, mid))
        if estimates:
            estimates.sort()
            return estimates[0][1], estimates[0][0]
        return None

    def get_spend(self, user_id: Optional[str] = None, model_id: Optional[str] = None) -> float:
        total = 0.0
        for u in self._usage:
            if user_id and u.user_id != user_id:
                continue
            if model_id and u.model_id != model_id:
                continue
            total += getattr(u, "cost", self.estimate(u.model_id, u.input_tokens, u.output_tokens))
        return round(total, 4)

    def get_report(self) -> Dict[str, Any]:
        by_model = defaultdict(float)
        by_user = defaultdict(float)
        total = 0.0
        for u in self._usage:
            cost = getattr(u, "cost", self.estimate(u.model_id, u.input_tokens, u.output_tokens))
            by_model[u.model_id] += cost
            by_user[u.user_id] += cost
            total += cost
        return {
            "total_spend": round(total, 4),
            "budget_limit": self.budget_limit,
            "budget_used": f"{(total / max(self.budget_limit, 1) * 100):.1f}%",
            "by_model": {k: round(v, 4) for k, v in by_model.items()},
            "by_user": {k: round(v, 4) for k, v in by_user.items()},
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_ratio": f"{(self._cache_hits / max(self._cache_hits + self._cache_misses, 1) * 100):.1f}%",
            "alert": total > self.budget_limit,
        }

    def get_stats(self) -> Dict[str, Any]:
        return self.get_report()


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Cost Optimizer Engine")
    print("ai/llm_cost_optimizer_native.py")
    print("=" * 60)

    engine = CostOptimizerEngine(budget_limit=50.0)

    # Set pricing
    engine.set_pricing(ModelPricing("gpt-4", 0.03, 0.06))
    engine.set_pricing(ModelPricing("gpt-3.5", 0.0015, 0.002))
    engine.set_pricing(ModelPricing("claude", 0.008, 0.024))

    # 1. Estimate costs
    print("\n[1] Cost Estimation")
    for model in ["gpt-4", "gpt-3.5", "claude"]:
        cost = engine.estimate(model, 1000, 500)
        print(f"  {model}: ${cost:.4f} (1000 in + 500 out)")

    # 2. Cheapest for task
    print("\n[2] Cheapest Model")
    cheapest = engine.cheapest_for(1000, 500, ["gpt-4", "gpt-3.5", "claude"])
    print(f"  Cheapest: {cheapest[0]} at ${cheapest[1]:.4f}")

    # 3. Record usage
    print("\n[3] Record Usage")
    usage_records = [
        UsageRecord("gpt-4", 2000, 1000, time.time(), "alice"),
        UsageRecord("gpt-3.5", 3000, 1500, time.time(), "bob"),
        UsageRecord("gpt-3.5", 1000, 500, time.time(), "alice"),
        UsageRecord("gpt-4", 500, 200, time.time(), "bob", cached=True),
    ]
    for u in usage_records:
        cost = engine.record(u)
        print(f"  {u.user_id} / {u.model_id}: ${cost:.4f} (cached={u.cached})")

    # 4. Spend by user
    print("\n[4] Spend by User")
    for user in ["alice", "bob"]:
        print(f"  {user}: ${engine.get_spend(user_id=user):.4f}")

    # 5. Report
    print("\n[5] Cost Report")
    report = engine.get_report()
    print(f"  Total: ${report['total_spend']}")
    print(f"  Budget: {report['budget_used']}")
    print(f"  Cache: {report['cache_ratio']}")
    print(f"  Alert: {report['alert']}")
    print(f"  By model: {report['by_model']}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
