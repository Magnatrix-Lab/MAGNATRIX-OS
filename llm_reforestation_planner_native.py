"""Reforestation Planner — spacing, survival, growth, carbon, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class ReforestationPlanner:
    area_ha: float = 10.0
    spacing_m: float = 3.0
    survival_rate: float = 0.8
    growth_rate: float = 0.5
    """m/year"""
    target_carbon: float = 100.0
    """tonnes"""

    def trees_needed(self) -> int:
        area_m2 = self.area_ha * 10000
        tree_area = self.spacing_m ** 2
        return int(area_m2 / tree_area)

    def expected_survivors(self) -> int:
        return int(self.trees_needed() * self.survival_rate)

    def time_to_canopy(self, target_height: float = 10.0) -> float:
        return target_height / self.growth_rate if self.growth_rate > 0 else float('inf')

    def carbon_per_tree(self) -> float:
        return self.target_carbon / self.expected_survivors() if self.expected_survivors() > 0 else 0.0

    def annual_carbon(self, years: int = 10) -> float:
        return self.target_carbon * min(1.0, years / self.time_to_canopy(10))

    def cost_estimate(self, cost_per_seedling: float = 2.0, labor_cost_per_ha: float = 500.0) -> float:
        return self.trees_needed() * cost_per_seedling + self.area_ha * labor_cost_per_ha

    def stats(self) -> Dict:
        return {
            "trees_needed": self.trees_needed(),
            "expected_survivors": self.expected_survivors(),
            "time_to_canopy": round(self.time_to_canopy(), 1),
            "cost": round(self.cost_estimate(), 0)
        }

def run():
    rp = ReforestationPlanner(area_ha=50, spacing_m=2.5, survival_rate=0.75, growth_rate=0.8, target_carbon=500)
    print(rp.stats())
    print("Annual carbon 5yr:", rp.annual_carbon(5))

if __name__ == "__main__":
    run()
