"""Native stdlib module: Inventory Optimizer
Calculates EOQ, reorder points, and safety stock for inventory management.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class InventoryOptimizer:
    annual_demand: float
    order_cost: float
    holding_cost_per_unit: float
    lead_time_days: float
    daily_demand_std: float = 0.0
    service_level_z: float = 1.65

    def eoq(self) -> float:
        if self.holding_cost_per_unit <= 0:
            return 0.0
        return math.sqrt((2 * self.annual_demand * self.order_cost) / self.holding_cost_per_unit)

    def reorder_point(self) -> float:
        daily_demand = self.annual_demand / 365
        return daily_demand * self.lead_time_days

    def safety_stock(self) -> float:
        return self.service_level_z * self.daily_demand_std * math.sqrt(self.lead_time_days)

    def total_annual_cost(self) -> float:
        q = self.eoq()
        if q == 0:
            return 0.0
        ordering = (self.annual_demand / q) * self.order_cost
        holding = (q / 2) * self.holding_cost_per_unit
        return ordering + holding

    def stats(self) -> Dict[str, float]:
        return {
            "eoq": round(self.eoq(), 1),
            "reorder_point": round(self.reorder_point(), 1),
            "safety_stock": round(self.safety_stock(), 1),
            "total_annual_cost": round(self.total_annual_cost(), 2),
        }

def run():
    io = InventoryOptimizer(annual_demand=12000, order_cost=50, holding_cost_per_unit=2.5, lead_time_days=7, daily_demand_std=15)
    print(io.stats())

if __name__ == "__main__":
    run()
