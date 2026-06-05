"""Native stdlib module: Binding Cost Calculator
Estimates binding costs by method, page count, and quantity.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class BindingType(Enum):
    SADDLE_STITCH = "saddle_stitch"
    PERFECT_BOUND = "perfect_bound"
    SPIRAL = "spiral"
    WIRE_O = "wire_o"
    CASE_BOUND = "case_bound"

@dataclass
class BindingCostCalculator:
    job_name: str
    page_count: int
    quantity: int
    binding_type: BindingType
    base_cost_per_unit: float = 0.50

    def _multiplier(self) -> float:
        multipliers = {
            BindingType.SADDLE_STITCH: 0.8,
            BindingType.PERFECT_BOUND: 1.0,
            BindingType.SPIRAL: 1.2,
            BindingType.WIRE_O: 1.5,
            BindingType.CASE_BOUND: 3.0,
        }
        return multipliers.get(self.binding_type, 1.0)

    def _page_factor(self) -> float:
        if self.page_count <= 16:
            return 0.8
        elif self.page_count <= 64:
            return 1.0
        elif self.page_count <= 200:
            return 1.3
        return 1.8

    def cost_per_unit(self) -> float:
        return self.base_cost_per_unit * self._multiplier() * self._page_factor()

    def total_cost(self) -> float:
        return self.cost_per_unit() * self.quantity

    def stats(self) -> Dict[str, float]:
        return {
            "job": self.job_name,
            "binding": self.binding_type.value,
            "pages": self.page_count,
            "quantity": self.quantity,
            "cost_per_unit": round(self.cost_per_unit(), 2),
            "total_cost": round(self.total_cost(), 2),
        }

def run():
    bcc = BindingCostCalculator(job_name="Annual Report", page_count=48, quantity=500, binding_type=BindingType.PERFECT_BOUND)
    print(bcc.stats())

if __name__ == "__main__":
    run()
