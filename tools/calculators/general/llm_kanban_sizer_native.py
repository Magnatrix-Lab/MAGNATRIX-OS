"""Native stdlib module: Kanban Sizer
Calculates kanban card quantities and container sizes for pull systems.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class KanbanSizer:
    part_name: str
    daily_demand: float
    lead_time_days: float
    container_size: int
    safety_days: float = 1.0
    policy_variable: float = 1.0

    def demand_during_lead_time(self) -> float:
        return self.daily_demand * self.lead_time_days

    def safety_stock(self) -> float:
        return self.daily_demand * self.safety_days

    def total_kanban_quantity(self) -> float:
        return (self.demand_during_lead_time() + self.safety_stock()) * self.policy_variable

    def num_kanbans(self) -> int:
        if self.container_size == 0:
            return 0
        return math.ceil(self.total_kanban_quantity() / self.container_size)

    def inventory_max(self) -> int:
        return self.num_kanbans() * self.container_size

    def stats(self) -> Dict[str, float]:
        return {
            "part": self.part_name,
            "demand_lead_time": round(self.demand_during_lead_time(), 1),
            "safety_stock": round(self.safety_stock(), 1),
            "total_kanban_qty": round(self.total_kanban_quantity(), 1),
            "num_kanbans": self.num_kanbans(),
            "inventory_max": self.inventory_max(),
        }

def run():
    ks = KanbanSizer(part_name="Bolt-M8", daily_demand=200, lead_time_days=3, container_size=50, safety_days=1.5)
    print(ks.stats())

if __name__ == "__main__":
    run()
