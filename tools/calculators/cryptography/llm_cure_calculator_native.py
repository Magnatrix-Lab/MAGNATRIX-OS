"""Native stdlib module: Cure Calculator
Calculates dry-cure and brine concentrations for meat preservation.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class CureCalculator:
    meat_weight_g: float
    salt_pct: float = 2.5
    sugar_pct: float = 1.0
    cure_1_pct: float = 0.25
    water_g: float = 0.0

    def salt_g(self) -> float:
        return self.meat_weight_g * (self.salt_pct / 100)

    def sugar_g(self) -> float:
        return self.meat_weight_g * (self.sugar_pct / 100)

    def cure_1_g(self) -> float:
        return self.meat_weight_g * (self.cure_1_pct / 100)

    def brine_total_weight(self) -> float:
        return self.meat_weight_g + self.water_g

    def brine_concentration(self) -> float:
        if self.water_g == 0:
            return 0.0
        return (self.salt_g() / self.brine_total_weight()) * 100

    def stats(self) -> Dict[str, float]:
        return {
            "salt_g": round(self.salt_g(), 2),
            "sugar_g": round(self.sugar_g(), 2),
            "cure_1_g": round(self.cure_1_g(), 2),
            "brine_total_g": round(self.brine_total_weight(), 2),
            "brine_concentration_pct": round(self.brine_concentration(), 3),
        }

def run():
    cc = CureCalculator(meat_weight_g=5000, salt_pct=2.5, sugar_pct=1.5, cure_1_pct=0.25, water_g=3000)
    print(cc.stats())

if __name__ == "__main__":
    run()
