"""Inventory Forecaster — demand, reorder, safety stock, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class InventoryForecaster:
    demand_history: List[float] = field(default_factory=list)
    lead_time: int = 7
    service_level: float = 0.95

    def avg_demand(self) -> float:
        return sum(self.demand_history) / len(self.demand_history) if self.demand_history else 0.0

    def demand_std(self) -> float:
        if len(self.demand_history) < 2:
            return 0.0
        m = self.avg_demand()
        return math.sqrt(sum((d - m)**2 for d in self.demand_history) / len(self.demand_history))

    def reorder_point(self) -> float:
        return self.avg_demand() * self.lead_time + self.safety_stock()

    def safety_stock(self) -> float:
        z = 1.65 if self.service_level == 0.95 else 2.33 if self.service_level == 0.99 else 1.28
        return z * self.demand_std() * math.sqrt(self.lead_time)

    def eoq(self, order_cost: float = 50, holding_cost: float = 2) -> float:
        d = self.avg_demand() * 365
        return math.sqrt(2 * d * order_cost / holding_cost)

    def stockout_probability(self, current_stock: float) -> float:
        if self.demand_std() == 0:
            return 0.0
        z = (current_stock - self.avg_demand() * self.lead_time) / (self.demand_std() * math.sqrt(self.lead_time))
        return 1 - min(1, max(0, 0.5 + z * 0.3))

    def stats(self) -> Dict:
        return {"avg_demand": round(self.avg_demand(), 1), "reorder_point": round(self.reorder_point(), 1), "safety_stock": round(self.safety_stock(), 1)}

def run():
    ifc = InventoryForecaster(demand_history=[10,12,15,11,13,14,12], lead_time=5)
    print(ifc.stats())
    print("EOQ:", ifc.eoq())
    print("Stockout prob at 50:", ifc.stockout_probability(50))

if __name__ == "__main__":
    run()
