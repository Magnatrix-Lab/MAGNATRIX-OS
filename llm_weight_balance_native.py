"""Weight and Balance Calculator — CG, moment, envelope, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class WeightItem:
    name: str
    weight: float
    arm: float

class WeightBalance:
    def __init__(self):
        self.items: List[WeightItem] = []
        self.empty_weight: float = 5000.0
        self.empty_arm: float = 40.0

    def add_item(self, item: WeightItem):
        self.items.append(item)

    def total_weight(self) -> float:
        return self.empty_weight + sum(i.weight for i in self.items)

    def total_moment(self) -> float:
        return self.empty_weight * self.empty_arm + sum(i.weight * i.arm for i in self.items)

    def cg(self) -> float:
        return self.total_moment() / self.total_weight() if self.total_weight() > 0 else 0.0

    def in_envelope(self, min_cg: float = 35.0, max_cg: float = 45.0, max_weight: float = 10000.0) -> bool:
        cg = self.cg()
        return min_cg <= cg <= max_cg and self.total_weight() <= max_weight

    def fuel_to_add(self, target_cg: float, fuel_arm: float = 40.0) -> float:
        current_w = self.total_weight()
        current_m = self.total_moment()
        if fuel_arm == target_cg:
            return 0.0
        return (current_w * target_cg - current_m) / (fuel_arm - target_cg) if fuel_arm != target_cg else 0.0

    def stats(self) -> Dict:
        return {
            "total_weight": round(self.total_weight(), 1),
            "cg": round(self.cg(), 2),
            "in_envelope": self.in_envelope()
        }

def run():
    wb = WeightBalance()
    wb.add_item(WeightItem("Pilot", 80, 37))
    wb.add_item(WeightItem("Passenger", 75, 60))
    wb.add_item(WeightItem("Baggage", 50, 80))
    print(wb.stats())
    print("Fuel to add:", wb.fuel_to_add(42.0))

if __name__ == "__main__":
    run()
