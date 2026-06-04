"""Harvest Optimizer — maturity, window, labor, storage, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class HarvestOptimizer:
    maturity: float = 0.5
    days_to_mature: int = 30
    labor_capacity: float = 10.0
    storage_capacity: float = 1000.0
    expected_yield: float = 500.0

    def readiness(self) -> float:
        return min(1.0, self.maturity + (30 - self.days_to_mature) / 30)

    def optimal_date(self, days_window: int = 7) -> int:
        for day in range(days_window + 1):
            m = self.maturity + day * 0.05
            if m >= 0.95:
                return day
        return days_window

    def labor_needed(self) -> float:
        return self.expected_yield / 50

    def storage_ok(self) -> bool:
        return self.expected_yield <= self.storage_capacity

    def schedule(self, fields: List[Dict]) -> List[Dict]:
        return sorted(fields, key=lambda f: f.get("maturity", 0), reverse=True)

    def stats(self) -> Dict:
        return {"readiness": round(self.readiness(), 2), "optimal_day": self.optimal_date(), "labor": self.labor_needed(), "storage_ok": self.storage_ok()}

def run():
    ho = HarvestOptimizer(maturity=0.8, expected_yield=800)
    print(ho.stats())
    print("Schedule:", ho.schedule([{"name": "A", "maturity": 0.9}, {"name": "B", "maturity": 0.7}]))

if __name__ == "__main__":
    run()
