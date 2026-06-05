"""Circular Economy -- reuse, repair, remanufacture, recycling rate, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class CircularEconomy:
    total_products: int = 1000
    reused: int = 100
    repaired: int = 150
    remanufactured: int = 50
    recycled: int = 300
    landfilled: int = 400

    def circularity_rate(self) -> float:
        total = self.reused + self.repaired + self.remanufactured + self.recycled + self.landfilled
        return (self.reused + self.repaired + self.remanufactured + self.recycled) / total if total > 0 else 0.0

    def landfill_rate(self) -> float:
        total = self.reused + self.repaired + self.remanufactured + self.recycled + self.landfilled
        return self.landfilled / total if total > 0 else 0.0

    def value_retention(self) -> Dict[str, float]:
        return {
            "reuse": 0.95,
            "repair": 0.85,
            "remanufacture": 0.70,
            "recycling": 0.30,
            "landfill": 0.0
        }

    def weighted_value(self) -> float:
        values = self.value_retention()
        total = self.reused + self.repaired + self.remanufactured + self.recycled + self.landfilled
        if total == 0:
            return 0.0
        return (self.reused * values["reuse"] + self.repaired * values["repair"] + 
                self.remanufactured * values["remanufacture"] + self.recycled * values["recycling"]) / total

    def improvement_potential(self) -> Dict[str, int]:
        return {
            "increase_reuse": max(0, self.landfilled - self.reused),
            "increase_repair": max(0, self.landfilled - self.repaired),
            "increase_recycle": max(0, self.landfilled - self.recycled)
        }

    def stats(self) -> Dict:
        return {"circularity": round(self.circularity_rate(), 3), "landfill_rate": round(self.landfill_rate(), 3), "value_retention": round(self.weighted_value(), 3)}

def run():
    ce = CircularEconomy()
    print(ce.stats())
    print("Potential:", ce.improvement_potential())

if __name__ == "__main__":
    run()
