"""Cost Optimizer — Token usage tracking, budget enforcement, and cost estimation.

Modul ini menyediakan:
- CostModel untuk pricing per model/provider (OpenAI, Anthropic, local)
- UsageTracker untuk real-time dan histori penggunaan token
- BudgetEnforcer untuk hard/soft budget limits dengan alerting
- CostEstimator untuk prediksi biaya sebelum query
- CostReport untuk laporan pengeluaran dan optimasi
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum, auto


class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CUSTOM = "custom"


class BudgetType(Enum):
    HARD = "hard"  # Block when exceeded
    SOFT = "soft"  # Warn when exceeded
    DYNAMIC = "dynamic"  # Adjust based on priority


@dataclass
class PriceRate:
    """Price per 1K tokens."""
    provider: Provider
    model: str
    input_price: float  # per 1K tokens
    output_price: float  # per 1K tokens
    currency: str = "USD"


@dataclass
class UsageRecord:
    """Single usage record."""
    record_id: str
    provider: Provider
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: float
    cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.cost == 0.0:
            self.cost = 0.0  # Will be calculated by CostModel


@dataclass
class BudgetRule:
    """Budget rule definition."""
    rule_id: str
    name: str
    budget_type: BudgetType
    limit: float  # in currency
    period: str  # daily, weekly, monthly, per_query
    current: float = 0.0
    alert_threshold: float = 0.8  # Alert at 80%
    alerted: bool = False


class CostModel:
    """Define and lookup pricing models."""

    # Default rates (approximate, in USD per 1K tokens)
    DEFAULT_RATES: List[PriceRate] = [
        PriceRate(Provider.OPENAI, "gpt-4o", 0.005, 0.015),
        PriceRate(Provider.OPENAI, "gpt-4o-mini", 0.00015, 0.0006),
        PriceRate(Provider.OPENAI, "gpt-3.5-turbo", 0.0005, 0.0015),
        PriceRate(Provider.ANTHROPIC, "claude-3-5-sonnet", 0.003, 0.015),
        PriceRate(Provider.ANTHROPIC, "claude-3-haiku", 0.00025, 0.00125),
        PriceRate(Provider.LOCAL, "llama-3-70b", 0.0, 0.0),
        PriceRate(Provider.LOCAL, "qwen-2.5-72b", 0.0, 0.0),
        PriceRate(Provider.CUSTOM, "custom-model", 0.001, 0.002),
    ]

    def __init__(self):
        self._rates: Dict[Tuple[str, str], PriceRate] = {}
        for rate in self.DEFAULT_RATES:
            self._rates[(rate.provider.value, rate.model)] = rate
        self._custom_calculators: Dict[str, Callable[[int, int], float]] = {}

    def get_rate(self, provider: Provider, model: str) -> Optional[PriceRate]:
        return self._rates.get((provider.value, model))

    def set_rate(self, rate: PriceRate) -> None:
        self._rates[(rate.provider.value, rate.model)] = rate

    def calculate(self, provider: Provider, model: str, input_tokens: int, output_tokens: int) -> float:
        rate = self.get_rate(provider, model)
        if not rate:
            # Fallback: use custom calculator or zero
            calc = self._custom_calculators.get(f"{provider.value}:{model}")
            if calc:
                return calc(input_tokens, output_tokens)
            return 0.0
        cost = (input_tokens / 1000.0) * rate.input_price + (output_tokens / 1000.0) * rate.output_price
        return round(cost, 6)

    def set_custom_calculator(self, provider: str, model: str, fn: Callable[[int, int], float]) -> None:
        self._custom_calculators[f"{provider}:{model}"] = fn

    def list_rates(self) -> List[PriceRate]:
        return list(self._rates.values())


class UsageTracker:
    """Track all usage records with aggregation."""

    def __init__(self, cost_model: Optional[CostModel] = None):
        self.cost_model = cost_model or CostModel()
        self._records: List[UsageRecord] = []
        self._by_provider: Dict[Provider, List[UsageRecord]] = {p: [] for p in Provider}
        self._by_model: Dict[str, List[UsageRecord]] = {}

    def record(self, provider: Provider, model: str, input_tokens: int, output_tokens: int,
               metadata: Optional[Dict[str, Any]] = None) -> UsageRecord:
        import uuid
        cost = self.cost_model.calculate(provider, model, input_tokens, output_tokens)
        rec = UsageRecord(
            record_id=str(uuid.uuid4())[:12],
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=time.time(),
            cost=cost,
            metadata=metadata or {}
        )
        self._records.append(rec)
        self._by_provider[provider].append(rec)
        self._by_model.setdefault(model, []).append(rec)
        return rec

    def get_stats(self, period: Optional[Tuple[float, float]] = None) -> Dict[str, Any]:
        records = self._records
        if period:
            records = [r for r in records if period[0] <= r.timestamp <= period[1]]
        total_cost = sum(r.cost for r in records)
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        return {
            "total_queries": len(records),
            "total_cost": round(total_cost, 4),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "by_provider": {
                p.value: {
                    "queries": len(self._by_provider[p]),
                    "cost": round(sum(r.cost for r in self._by_provider[p]), 4),
                }
                for p in Provider
            },
            "by_model": {
                m: {
                    "queries": len(recs),
                    "cost": round(sum(r.cost for r in recs), 4),
                }
                for m, recs in self._by_model.items()
            },
        }

    def get_records(self) -> List[UsageRecord]:
        return self._records

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{
                "record_id": r.record_id,
                "provider": r.provider.value,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost": r.cost,
                "timestamp": r.timestamp,
            } for r in self._records], f, indent=2)


class BudgetEnforcer:
    """Enforce budget limits with alerting."""

    def __init__(self, cost_model: Optional[CostModel] = None):
        self.cost_model = cost_model or CostModel()
        self._rules: Dict[str, BudgetRule] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._callbacks: List[Callable[[str, BudgetRule], None]] = []

    def add_rule(self, rule: BudgetRule) -> None:
        self._rules[rule.rule_id] = rule

    def check(self, provider: Provider, model: str, input_tokens: int, output_tokens: int,
              rule_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        cost = self.cost_model.calculate(provider, model, input_tokens, output_tokens)
        if rule_id and rule_id in self._rules:
            rule = self._rules[rule_id]
            rule.current += cost
            if rule.current >= rule.limit:
                if rule.budget_type == BudgetType.HARD:
                    return False, f"Budget exceeded: {rule.name} ({rule.current:.4f} / {rule.limit:.4f})"
                elif rule.budget_type == BudgetType.SOFT and not rule.alerted:
                    rule.alerted = True
                    self._fire_alert(rule)
                    return True, f"Budget warning: {rule.name} exceeded"
            elif rule.current >= rule.limit * rule.alert_threshold and not rule.alerted:
                rule.alerted = True
                self._fire_alert(rule)
                return True, f"Budget alert: {rule.name} at {rule.current / rule.limit:.0%}"
        return True, None

    def _fire_alert(self, rule: BudgetRule) -> None:
        alert = {"rule_id": rule.rule_id, "name": rule.name, "current": rule.current, "limit": rule.limit, "timestamp": time.time()}
        self._alerts.append(alert)
        for cb in self._callbacks:
            cb(rule.rule_id, rule)

    def on_alert(self, callback: Callable[[str, BudgetRule], None]) -> None:
        self._callbacks.append(callback)

    def reset(self, rule_id: str) -> None:
        if rule_id in self._rules:
            self._rules[rule_id].current = 0.0
            self._rules[rule_id].alerted = False

    def reset_all(self) -> None:
        for rule in self._rules.values():
            rule.current = 0.0
            rule.alerted = False

    def get_alerts(self) -> List[Dict[str, Any]]:
        return self._alerts

    def get_status(self) -> Dict[str, Any]:
        return {
            r.rule_id: {
                "name": r.name,
                "type": r.budget_type.value,
                "limit": r.limit,
                "current": round(r.current, 4),
                "remaining": round(r.limit - r.current, 4),
                "percent_used": round(r.current / max(r.limit, 1e-9) * 100, 1),
                "alerted": r.alerted,
            }
            for r in self._rules.values()
        }


class CostEstimator:
    """Estimate cost before executing a query."""

    def __init__(self, cost_model: Optional[CostModel] = None):
        self.cost_model = cost_model or CostModel()

    def estimate(self, provider: Provider, model: str, input_text: str, expected_output_tokens: int = 500) -> Dict[str, Any]:
        # Approximate token count
        words = len(input_text.split())
        input_tokens = int(words / 0.75)  # Rough estimate
        cost = self.cost_model.calculate(provider, model, input_tokens, expected_output_tokens)
        return {
            "provider": provider.value,
            "model": model,
            "estimated_input_tokens": input_tokens,
            "estimated_output_tokens": expected_output_tokens,
            "estimated_cost": round(cost, 6),
            "currency": "USD",
        }

    def compare_models(self, input_text: str, expected_output_tokens: int = 500) -> List[Dict[str, Any]]:
        results = []
        for rate in self.cost_model.list_rates():
            est = self.estimate(rate.provider, rate.model, input_text, expected_output_tokens)
            results.append({**est, "input_price": rate.input_price, "output_price": rate.output_price})
        return sorted(results, key=lambda x: x["estimated_cost"])

    def recommend(self, input_text: str, expected_output_tokens: int = 500, max_budget: Optional[float] = None) -> Optional[str]:
        comparisons = self.compare_models(input_text, expected_output_tokens)
        if max_budget is not None:
            valid = [c for c in comparisons if c["estimated_cost"] <= max_budget]
            if valid:
                return valid[0]["model"]
            return None
        return comparisons[0]["model"] if comparisons else None


class CostReport:
    """Generate cost reports and optimization suggestions."""

    def __init__(self, tracker: UsageTracker):
        self.tracker = tracker

    def generate(self, period_days: int = 30) -> Dict[str, Any]:
        now = time.time()
        start = now - (period_days * 86400)
        stats = self.tracker.get_stats(period=(start, now))
        records = [r for r in self.tracker.get_records() if start <= r.timestamp <= now]

        # Find most expensive queries
        top_expensive = sorted(records, key=lambda r: r.cost, reverse=True)[:5]

        # Find cheapest provider for equivalent workload
        provider_costs = {}
        for p in Provider:
            precs = [r for r in records if r.provider == p]
            if precs:
                provider_costs[p.value] = sum(r.cost for r in precs) / max(len(precs), 1)

        suggestions = []
        if stats["by_model"]:
            most_expensive_model = max(stats["by_model"].items(), key=lambda x: x[1]["cost"])
            suggestions.append(f"Consider using cheaper alternative for {most_expensive_model[0]}")
        if provider_costs.get("local", 0) == 0 and any(r.provider != Provider.LOCAL for r in records):
            suggestions.append("Local models are free — consider using local inference for non-critical queries")

        return {
            "period_days": period_days,
            "stats": stats,
            "top_expensive": [{"model": r.model, "cost": r.cost, "tokens": r.input_tokens + r.output_tokens} for r in top_expensive],
            "avg_per_provider": provider_costs,
            "suggestions": suggestions,
            "generated_at": now,
        }

    def export(self, path: str, period_days: int = 30) -> None:
        report = self.generate(period_days)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("COST OPTIMIZER DEMO")
    print("=" * 70)

    cost_model = CostModel()

    # 1. Price rates
    print("\n[1] Price Rates")
    for rate in cost_model.list_rates():
        print(f"  {rate.provider.value:10} {rate.model:25} in=${rate.input_price:>8}/1K out=${rate.output_price:>8}/1K")

    # 2. Cost calculation
    print("\n[2] Cost Calculation")
    queries = [
        (Provider.OPENAI, "gpt-4o", 2000, 500),
        (Provider.OPENAI, "gpt-4o-mini", 2000, 500),
        (Provider.ANTHROPIC, "claude-3-5-sonnet", 2000, 500),
        (Provider.LOCAL, "llama-3-70b", 2000, 500),
    ]
    for prov, model, inp, out in queries:
        cost = cost_model.calculate(prov, model, inp, out)
        print(f"  {model:25} {inp:>5}in + {out:>5}out = ${cost:.6f}")

    # 3. Usage tracking
    print("\n[3] Usage Tracking")
    tracker = UsageTracker(cost_model)
    for _ in range(10):
        tracker.record(Provider.OPENAI, "gpt-4o", 1500, 400, {"user": "alice"})
        tracker.record(Provider.OPENAI, "gpt-4o-mini", 1500, 400, {"user": "bob"})
        tracker.record(Provider.ANTHROPIC, "claude-3-5-sonnet", 1500, 400, {"user": "charlie"})
    stats = tracker.get_stats()
    print(f"  Total queries: {stats['total_queries']}")
    print(f"  Total cost: ${stats['total_cost']:.4f}")
    print(f"  Total tokens: {stats['total_tokens']}")
    for prov, data in stats['by_provider'].items():
        if data['queries'] > 0:
            print(f"    {prov}: {data['queries']} queries, ${data['cost']:.4f}")

    # 4. Budget enforcement
    print("\n[4] Budget Enforcement")
    enforcer = BudgetEnforcer(cost_model)
    enforcer.add_rule(BudgetRule("rule-1", "Daily Budget", BudgetType.HARD, limit=5.0, period="daily"))
    enforcer.add_rule(BudgetRule("rule-2", "Monthly Alert", BudgetType.SOFT, limit=100.0, period="monthly", alert_threshold=0.5))
    for i in range(3):
        ok, msg = enforcer.check(Provider.OPENAI, "gpt-4o", 50000, 10000, "rule-1")
        print(f"  Query {i+1}: {'✅' if ok else '❌'} {msg or 'OK'}")
    print(f"  Budget status: {enforcer.get_status()}")

    # 5. Cost estimation
    print("\n[5] Cost Estimation")
    estimator = CostEstimator(cost_model)
    text = "Explain quantum computing in simple terms with examples."
    est = estimator.estimate(Provider.OPENAI, "gpt-4o", text, expected_output_tokens=800)
    print(f"  Estimation: {est}")
    print(f"  Comparison (cheapest first):")
    for comp in estimator.compare_models(text, 800)[:3]:
        print(f"    {comp['model']:25} ${comp['estimated_cost']:.6f}")
    rec = estimator.recommend(text, 800, max_budget=0.01)
    print(f"  Recommended model for $0.01 budget: {rec}")

    # 6. Cost report
    print("\n[6] Cost Report")
    report = CostReport(tracker)
    r = report.generate(period_days=1)
    print(f"  Suggestions: {r['suggestions']}")
    print(f"  Top expensive: {r['top_expensive'][:2]}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
