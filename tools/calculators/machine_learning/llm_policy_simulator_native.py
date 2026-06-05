"""Policy Simulator — impact, cost-benefit, distributional, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class PolicySimulator:
    population: float = 1000000.0
    affected_pct: float = 0.1
    cost_per_capita: float = 100.0
    benefit_per_capita: float = 150.0

    def affected_population(self) -> float:
        return self.population * self.affected_pct

    def total_cost(self) -> float:
        return self.affected_population() * self.cost_per_capita

    def total_benefit(self) -> float:
        return self.affected_population() * self.benefit_per_capita

    def net_benefit(self) -> float:
        return self.total_benefit() - self.total_cost()

    def bcr(self) -> float:
        return self.total_benefit() / self.total_cost() if self.total_cost() > 0 else 0.0

    def cost_per_qaly(self, qaly_gained: float) -> float:
        return self.total_cost() / qaly_gained if qaly_gained > 0 else float('inf')

    def gini_impact(self, before: List[float], after: List[float]) -> float:
        def gini(x):
            n = len(x)
            if n == 0: return 0.0
            x_sorted = sorted(x)
            cumsum = sum((2 * (i + 1) - n - 1) * x_sorted[i] for i in range(n))
            return cumsum / (n * sum(x_sorted)) if sum(x_sorted) > 0 else 0.0
        return gini(after) - gini(before)

    def stats(self) -> Dict:
        return {"cost": round(self.total_cost(), 0), "benefit": round(self.total_benefit(), 0), "bcr": round(self.bcr(), 2), "net": round(self.net_benefit(), 0)}

def run():
    ps = PolicySimulator(affected_pct=0.2, cost_per_capita=200, benefit_per_capita=500)
    print(ps.stats())
    print("Cost per QALY:", ps.cost_per_qaly(10000))

if __name__ == "__main__":
    run()
