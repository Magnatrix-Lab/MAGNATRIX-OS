"""Supply Chain Optimizer — inventory, EOQ, safety stock, reorder, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class SupplyChainOptimizer:
    demand_per_year: float = 1000.0
    order_cost: float = 100.0
    holding_cost_per_unit: float = 5.0
    lead_time_days: float = 7.0
    daily_demand: float = 10.0

    def eoq(self) -> float:
        return math.sqrt(2 * self.demand_per_year * self.order_cost / self.holding_cost_per_unit)

    def reorder_point(self, service_level: float = 0.95) -> float:
        return self.daily_demand * self.lead_time_days

    def safety_stock(self, demand_std: float, service_z: float = 1.65) -> float:
        return service_z * demand_std * math.sqrt(self.lead_time_days)

    def total_cost(self, order_qty: float) -> float:
        ordering = (self.demand_per_year / order_qty) * self.order_cost
        holding = (order_qty / 2) * self.holding_cost_per_unit
        return ordering + holding

    def cycle_time(self, order_qty: float) -> float:
        return order_qty / self.daily_demand

    def stats(self) -> Dict:
        q = self.eoq()
        return {"eoq": round(q, 1), "reorder": round(self.reorder_point(), 1), "total_cost": round(self.total_cost(q), 1)}

def run():
    sco = SupplyChainOptimizer()
    print(sco.stats())
    print("Safety stock:", sco.safety_stock(3))

if __name__ == "__main__":
    run()
