"""Native stdlib module: Wood Shrinkage Calculator
Calculates seasonal shrinkage, moisture content effects, and movement.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class WoodShrinkageCalculator:
    tangential_shrinkage_pct: float
    radial_shrinkage_pct: float
    current_mc_pct: float
    final_mc_pct: float = 6.0
    width_in: float = 6.0
    thickness_in: float = 1.0

    def shrinkage_multiplier(self) -> float:
        return (self.current_mc_pct - self.final_mc_pct) / (30 - 6)

    def width_change_in(self) -> float:
        return self.width_in * (self.tangential_shrinkage_pct / 100) * self.shrinkage_multiplier()

    def thickness_change_in(self) -> float:
        return self.thickness_in * (self.radial_shrinkage_pct / 100) * self.shrinkage_multiplier()

    def final_width_in(self) -> float:
        return self.width_in - self.width_change_in()

    def final_thickness_in(self) -> float:
        return self.thickness_in - self.thickness_change_in()

    def movement_risk(self) -> str:
        change = abs(self.width_change_in())
        if change < 0.02:
            return "low"
        elif change < 0.05:
            return "moderate"
        elif change < 0.1:
            return "high"
        return "extreme"

    def stats(self) -> Dict:
        return {
            "current_mc_pct": self.current_mc_pct,
            "final_mc_pct": self.final_mc_pct,
            "width_change_in": round(self.width_change_in(), 3),
            "thickness_change_in": round(self.thickness_change_in(), 3),
            "final_width_in": round(self.final_width_in(), 3),
            "final_thickness_in": round(self.final_thickness_in(), 3),
            "movement_risk": self.movement_risk(),
        }

def run():
    wsc = WoodShrinkageCalculator(tangential_shrinkage_pct=8.5, radial_shrinkage_pct=4.2, current_mc_pct=12, width_in=8, thickness_in=1.5)
    print(wsc.stats())

if __name__ == "__main__":
    run()
