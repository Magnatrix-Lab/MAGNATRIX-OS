"""Inventory Forecaster — demand, safety stock, reorder, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class InventoryForecaster:
    demand_history: List[float] = field(default_factory=list)
    lead_time: float = 7.0
    service_level: float = 0.95
    current_stock: float = 100.0

    def avg_demand(self) -> float:
        return sum(self.demand_history) / len(self.demand_history) if self.demand_history else 0.0

    def demand_std(self) -> float:
        if len(self.demand_history) < 2:
            return 0.0
        m = self.avg_demand()
        return math.sqrt(sum((d - m)**2 for d in self.demand_history) / len(self.demand_history))

    def safety_stock(self) -> float:
        z = 1.65 if self.service_level >= 0.95 else 1.28
        return z * self.demand_std() * math.sqrt(self.lead_time)

    def reorder_point(self) -> float:
        return self.avg_demand() * self.lead_time + self.safety_stock()

    def forecast_period(self, periods: int = 1) -> float:
        if not self.demand_history:
            return 0.0
        trend = (self.demand_history[-1] - self.demand_history[0]) / max(1, len(self.demand_history) - 1)
        return self.demand_history[-1] + trend * periods

    def stockout_risk(self) -> float:
        if self.current_stock <= 0:
            return 1.0
        expected = self.avg_demand() * self.lead_time
        return max(0, 1 - self.current_stock / expected) if expected > 0 else 0.0

    def stats(self) -> Dict:
        return {
            "avg_demand": round(self.avg_demand(), 1),
            "safety_stock": round(self.safety_stock(), 1),
            "reorder_point": round(self.reorder_point(), 1),
            "stockout_risk": round(self.stockout_risk(), 3)
        }

def run():
    inf = InventoryForecaster([10, 12, 11, 13, 15, 14, 16], lead_time=5, current_stock=80)
    print(inf.stats())
    print("Forecast:", inf.forecast_period(3))

if __name__ == "__main__":
    run()
