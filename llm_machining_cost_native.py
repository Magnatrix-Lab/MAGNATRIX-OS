"""Machining Cost Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class MachiningCost:
    machine_hour_rate: float
    setup_time_min: float
    machining_time_min: float
    tool_cost_per_part: float = 5.0
    material_cost: float = 20.0

    def setup_cost_per_part(self, batch_size: int = 100) -> float:
        if batch_size <= 0:
            return 0.0
        return round(self.machine_hour_rate * self.setup_time_min / 60.0 / batch_size, 2)

    def machining_cost_per_part(self) -> float:
        return round(self.machine_hour_rate * self.machining_time_min / 60.0, 2)

    def total_cost_per_part(self, batch_size: int = 100) -> float:
        return round(self.material_cost + self.setup_cost_per_part(batch_size) + self.machining_cost_per_part() + self.tool_cost_per_part, 2)

    def overhead_cost(self, overhead_percent: float = 30.0) -> float:
        return round(self.machining_cost_per_part() * overhead_percent / 100.0, 2)

    def total_with_overhead(self, batch_size: int = 100, overhead_percent: float = 30.0) -> float:
        return round(self.total_cost_per_part(batch_size) + self.overhead_cost(overhead_percent), 2)

    def cost_per_minute(self) -> float:
        return round(self.machine_hour_rate / 60.0, 3)

    def break_even_batch_size(self, target_price: float) -> float:
        cost = self.material_cost + self.machining_cost_per_part() + self.tool_cost_per_part
        if target_price <= cost:
            return 0.0
        setup = self.machine_hour_rate * self.setup_time_min / 60.0
        return round(setup / (target_price - cost), 0)

    def stats(self) -> Dict[str, float]:
        return {
            "machining_cost_per_part": self.machining_cost_per_part(),
            "total_cost_per_part": self.total_cost_per_part(),
            "cost_per_minute": self.cost_per_minute(),
        }

    def run(self):
        print("=" * 60)
        print("MACHINING COST CALCULATOR")
        print("=" * 60)
        mc = MachiningCost(
            machine_hour_rate=60, setup_time_min=30, machining_time_min=15,
            tool_cost_per_part=8, material_cost=35
        )
        print(f"Hour rate: ${mc.machine_hour_rate}")
        print(f"Setup cost/part (100): ${mc.setup_cost_per_part():.2f}")
        print(f"Machining cost/part: ${mc.machining_cost_per_part():.2f}")
        print(f"Total cost/part: ${mc.total_cost_per_part():.2f}")
        print(f"With overhead: ${mc.total_with_overhead():.2f}")
        print(f"Cost/min: ${mc.cost_per_minute():.3f}")
        print(f"Break-even @ $80: {mc.break_even_batch_size(80):.0f}")
        print(f"Stats: {mc.stats()}")

if __name__ == "__main__":
    MachiningCost(0, 0, 0).run()
