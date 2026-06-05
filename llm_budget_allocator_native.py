"""Budget Allocator — priority, efficiency, equity, optimization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class BudgetAllocator:
    total_budget: float = 1000000.0
    departments: List[Dict] = field(default_factory=list)
    """Each: {name, requested, priority, efficiency_score}"""

    def proportional_allocation(self) -> Dict[str, float]:
        total_req = sum(d["requested"] for d in self.departments)
        if total_req == 0:
            return {}
        return {d["name"]: d["requested"] / total_req * self.total_budget for d in self.departments}

    def priority_weighted(self) -> Dict[str, float]:
        weights = {d["name"]: d["priority"] * d["efficiency_score"] for d in self.departments}
        total_w = sum(weights.values())
        if total_w == 0:
            return {}
        return {name: w / total_w * self.total_budget for name, w in weights.items()}

    def equity_constrained(self, min_per_dept: float = 50000) -> Dict[str, float]:
        remaining = self.total_budget - min_per_dept * len(self.departments)
        if remaining < 0:
            return {d["name"]: self.total_budget / len(self.departments) for d in self.departments}
        base = {d["name"]: min_per_dept for d in self.departments}
        weights = {d["name"]: d["priority"] for d in self.departments}
        total_w = sum(weights.values())
        for name, w in weights.items():
            base[name] += w / total_w * remaining if total_w > 0 else 0
        return base

    def gini_coefficient(self, allocation: Dict[str, float]) -> float:
        vals = sorted(allocation.values())
        n = len(vals)
        if n == 0 or sum(vals) == 0:
            return 0.0
        cumsum = sum((2 * (i + 1) - n - 1) * vals[i] for i in range(n))
        return cumsum / (n * sum(vals))

    def stats(self) -> Dict:
        return {"departments": len(self.departments), "total": self.total_budget, "proportional_sum": sum(self.proportional_allocation().values())}

def run():
    ba = BudgetAllocator(1000000, [
        {"name": "Health", "requested": 400000, "priority": 5, "efficiency_score": 0.8},
        {"name": "Education", "requested": 300000, "priority": 4, "efficiency_score": 0.9},
        {"name": "Defense", "requested": 500000, "priority": 3, "efficiency_score": 0.6},
    ])
    print(ba.stats())
    print("Proportional:", ba.proportional_allocation())
    print("Priority:", ba.priority_weighted())

if __name__ == "__main__":
    run()
