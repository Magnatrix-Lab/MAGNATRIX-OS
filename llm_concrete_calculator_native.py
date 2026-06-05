"""Native stdlib module: Concrete Calculator
Calculates concrete volume, reinforcement, and curing time for slabs and footings.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ConcreteMix(Enum):
    C20 = 20
    C25 = 25
    C30 = 30
    C35 = 35
    C40 = 40

@dataclass
class ConcreteCalculator:
    element_name: str
    length_m: float
    width_m: float
    depth_m: float
    mix: ConcreteMix
    wastage_pct: float = 5.0
    cost_per_m3: float = 120.0

    def volume_m3(self) -> float:
        return self.length_m * self.width_m * self.depth_m

    def total_volume_m3(self) -> float:
        return self.volume_m3() * (1 + self.wastage_pct / 100)

    def cement_kg(self) -> float:
        return self.total_volume_m3() * 350

    def sand_kg(self) -> float:
        return self.total_volume_m3() * 700

    def aggregate_kg(self) -> float:
        return self.total_volume_m3() * 1200

    def water_l(self) -> float:
        return self.total_volume_m3() * 180

    def total_cost(self) -> float:
        return self.total_volume_m3() * self.cost_per_m3

    def curing_days(self) -> int:
        if self.mix.value >= 35:
            return 7
        return 3

    def stats(self) -> Dict:
        return {
            "element": self.element_name,
            "mix": f"C{self.mix.value}",
            "volume_m3": round(self.volume_m3(), 2),
            "total_volume_m3": round(self.total_volume_m3(), 2),
            "cement_kg": round(self.cement_kg(), 1),
            "sand_kg": round(self.sand_kg(), 1),
            "aggregate_kg": round(self.aggregate_kg(), 1),
            "water_l": round(self.water_l(), 1),
            "total_cost": round(self.total_cost(), 2),
            "curing_days": self.curing_days(),
        }

def run():
    cc = ConcreteCalculator(element_name="Slab", length_m=6, width_m=4, depth_m=0.15, mix=ConcreteMix.C25, cost_per_m3=130)
    print(cc.stats())

if __name__ == "__main__":
    run()
