"""
llm_cost_tracker_native.py
MAGNATRIX-OS Cost Tracker Engine
Native Python, stdlib only.
Provides token cost tracking, budget management, usage analytics, and billing projections.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class CostModel(Enum):
    PER_TOKEN = "per_token"
    PER_REQUEST = "per_request"
    PER_CHARACTER = "per_character"
    TIERED = "tiered"


@dataclass
class CostEntry:
    entry_id: str
    timestamp: float
    model: str
    operation: str
    input_units: float
    output_units: float
    cost_per_input: float
    cost_per_output: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return (self.input_units * self.cost_per_input) + (self.output_units * self.cost_per_output)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id, "timestamp": self.timestamp, "model": self.model,
            "operation": self.operation, "input_units": self.input_units,
            "output_units": self.output_units, "total_cost": round(self.total_cost, 6),
            "metadata": self.metadata, "tags": self.tags,
        }


@dataclass
class Budget:
    budget_id: str
    name: str
    limit: float
    period: str  # "daily", "weekly", "monthly"
    current_spend: float = 0.0
    alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "budget_id": self.budget_id, "name": self.name, "limit": self.limit,
            "period": self.period, "current_spend": round(self.current_spend, 4),
            "remaining": round(self.limit - self.current_spend, 4),
            "alerts": self.alerts,
        }


class CostTrackerEngine:
    """
    Cost tracking and budget management for LLM usage.
    """

    def __init__(self) -> None:
        self._entries: List[CostEntry] = []
        self._budgets: Dict[str, Budget] = {}
        self._models: Dict[str, Dict[str, float]] = {}  # model -> {input_cost, output_cost}
        self._handlers: List[Callable[[str, float], None]] = []
        self._entry_counter = 0

    def register_model(self, model: str, cost_per_input: float, cost_per_output: float) -> None:
        self._models[model] = {"input": cost_per_input, "output": cost_per_output}

    def record(self, model: str, operation: str, input_units: float, output_units: float,
               metadata: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None) -> CostEntry:
        self._entry_counter += 1
        entry_id = f"cost_{int(time.time() * 1000)}_{self._entry_counter}"
        rates = self._models.get(model, {"input": 0.0, "output": 0.0})
        entry = CostEntry(
            entry_id=entry_id, timestamp=time.time(), model=model, operation=operation,
            input_units=input_units, output_units=output_units,
            cost_per_input=rates["input"], cost_per_output=rates["output"],
            metadata=metadata or {}, tags=tags or []
        )
        self._entries.append(entry)
        self._update_budgets(entry.total_cost)
        return entry

    def _update_budgets(self, cost: float) -> None:
        for budget in self._budgets.values():
            budget.current_spend += cost
            if budget.current_spend > budget.limit * 0.8 and "80_percent" not in budget.alerts:
                budget.alerts.append("80_percent")
                for handler in self._handlers:
                    handler(budget.budget_id, budget.current_spend)
            if budget.current_spend > budget.limit and "over_limit" not in budget.alerts:
                budget.alerts.append("over_limit")
                for handler in self._handlers:
                    handler(budget.budget_id, budget.current_spend)

    def create_budget(self, budget: Budget) -> None:
        self._budgets[budget.budget_id] = budget

    def get_budget(self, budget_id: str) -> Optional[Budget]:
        return self._budgets.get(budget_id)

    def add_budget_handler(self, handler: Callable[[str, float], None]) -> None:
        self._handlers.append(handler)

    def get_total_cost(self, model: Optional[str] = None, start_time: Optional[float] = None,
                       end_time: Optional[float] = None) -> float:
        entries = self._entries
        if model:
            entries = [e for e in entries if e.model == model]
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]
        return sum(e.total_cost for e in entries)

    def get_by_model(self) -> Dict[str, float]:
        costs: Dict[str, float] = {}
        for e in self._entries:
            costs[e.model] = costs.get(e.model, 0.0) + e.total_cost
        return costs

    def get_by_operation(self) -> Dict[str, float]:
        costs: Dict[str, float] = {}
        for e in self._entries:
            costs[e.operation] = costs.get(e.operation, 0.0) + e.total_cost
        return costs

    def get_daily_summary(self, days: int = 7) -> Dict[str, float]:
        now = time.time()
        day_seconds = 86400
        summary: Dict[str, float] = {}
        for e in self._entries:
            day_key = time.strftime("%Y-%m-%d", time.localtime(e.timestamp))
            if e.timestamp >= now - (days * day_seconds):
                summary[day_key] = summary.get(day_key, 0.0) + e.total_cost
        return summary

    def get_top_models(self, n: int = 5) -> List[Dict[str, Any]]:
        by_model: Dict[str, Dict[str, Any]] = {}
        for e in self._entries:
            if e.model not in by_model:
                by_model[e.model] = {"model": e.model, "cost": 0.0, "requests": 0, "input_tokens": 0, "output_tokens": 0}
            by_model[e.model]["cost"] += e.total_cost
            by_model[e.model]["requests"] += 1
            by_model[e.model]["input_tokens"] += e.input_units
            by_model[e.model]["output_tokens"] += e.output_units
        sorted_models = sorted(by_model.values(), key=lambda x: x["cost"], reverse=True)
        return sorted_models[:n]

    def project_monthly(self, days_history: int = 7) -> float:
        now = time.time()
        history_cost = self.get_total_cost(start_time=now - days_history * 86400, end_time=now)
        daily_avg = history_cost / days_history
        return daily_avg * 30

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._entries], f, indent=2, default=str)

    def stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "total_cost": round(self.get_total_cost(), 6),
            "models_tracked": len(self._models),
            "budgets": len(self._budgets),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Cost Tracker Engine")
    print("=" * 60)

    engine = CostTrackerEngine()

    # Register model pricing
    engine.register_model("gpt-4o", 0.000005, 0.000015)
    engine.register_model("claude-3", 0.000003, 0.000015)
    engine.register_model("local-llm", 0.0, 0.0)

    # Create budget
    engine.create_budget(Budget("prod_budget", "Production Budget", 100.0, "monthly"))

    def budget_alert(budget_id: str, spend: float) -> None:
        print(f"  [BUDGET ALERT] {budget_id} spend: ${spend:.4f}")

    engine.add_budget_handler(budget_alert)

    print("\n--- Recording usage ---")
    for i in range(10):
        model = "gpt-4o" if i % 3 != 0 else "claude-3"
        entry = engine.record(model, "completion", input_units=1000, output_units=500,
                              metadata={"user_id": f"user_{i}"})
        print(f"  {entry.model}: ${entry.total_cost:.6f}")

    print("\n--- Stats ---")
    print(engine.stats())

    print("\n--- By model ---")
    for model, cost in engine.get_by_model().items():
        print(f"  {model}: ${cost:.6f}")

    print("\n--- Top models ---")
    for m in engine.get_top_models():
        print(f"  {m['model']}: ${m['cost']:.6f} ({m['requests']} requests)")

    print("\n--- Budget status ---")
    print(engine.get_budget("prod_budget").to_dict())

    print("\n--- Monthly projection ---")
    print(f"  Projected monthly: ${engine.project_monthly(7):.4f}")

    print("\nCost Tracker test complete.")


if __name__ == "__main__":
    run()
