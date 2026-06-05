"""Native stdlib module: Glass Compatibility Calculator
Checks COE matching, expansion coefficients, and compatibility.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class GlassCompatibilityCalculator:
    glass_a_coe: float
    glass_b_coe: float
    glass_a_thickness_mm: float = 3.0
    glass_b_thickness_mm: float = 3.0

    def coe_difference(self) -> float:
        return abs(self.glass_a_coe - self.glass_b_coe)

    def is_compatible(self, threshold: float = 3.0) -> bool:
        return self.coe_difference() <= threshold

    def compatibility_score(self) -> float:
        diff = self.coe_difference()
        return max(0, 100 - diff * 10)

    def weighted_average_coe(self, area_a: float = 1.0, area_b: float = 1.0) -> float:
        total = area_a * self.glass_a_thickness_mm + area_b * self.glass_b_thickness_mm
        if total == 0:
            return 0
        return (self.glass_a_coe * area_a * self.glass_a_thickness_mm +
                self.glass_b_coe * area_b * self.glass_b_thickness_mm) / total

    def stress_risk(self) -> str:
        diff = self.coe_difference()
        if diff <= 3:
            return "low"
        elif diff <= 5:
            return "moderate"
        elif diff <= 7:
            return "high"
        return "critical"

    def stats(self) -> Dict:
        return {
            "glass_a_coe": self.glass_a_coe,
            "glass_b_coe": self.glass_b_coe,
            "coe_difference": round(self.coe_difference(), 1),
            "compatible": self.is_compatible(),
            "compatibility_score": round(self.compatibility_score(), 1),
            "stress_risk": self.stress_risk(),
            "weighted_coe": round(self.weighted_average_coe(), 1),
        }

def run():
    gcc = GlassCompatibilityCalculator(glass_a_coe=96, glass_b_coe=94, glass_a_thickness_mm=4, glass_b_thickness_mm=2)
    print(gcc.stats())

if __name__ == "__main__":
    run()
