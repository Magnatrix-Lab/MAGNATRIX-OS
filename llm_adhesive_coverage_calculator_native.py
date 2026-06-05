"""Native stdlib module: Adhesive Coverage Calculator
Calculates glue coverage, PVA usage, and adhesive costs for bookbinding.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class AdhesiveCoverageCalculator:
    glue_type: str  # pva, methylcellulose, wheatpaste, hideglue
    area_to_cover_cm2: float
    glue_thickness_mm: float = 0.1
    layer_count: int = 1

    _COVERAGE_PER_ML = {
        "pva": 1000,
        "methylcellulose": 1200,
        "wheatpaste": 800,
        "hideglue": 900,
    }

    _COST_PER_ML = {
        "pva": 0.02,
        "methylcellulose": 0.015,
        "wheatpaste": 0.005,
        "hideglue": 0.03,
    }

    def coverage_per_ml(self) -> float:
        return self._COVERAGE_PER_ML.get(self.glue_type, 1000)

    def cost_per_ml(self) -> float:
        return self._COST_PER_ML.get(self.glue_type, 0.02)

    def glue_needed_ml(self) -> float:
        base = self.area_to_cover_cm2 / self.coverage_per_ml()
        return base * self.layer_count * (self.glue_thickness_mm / 0.1)

    def total_cost(self) -> float:
        return self.glue_needed_ml() * self.cost_per_ml()

    def drying_time_hours(self) -> float:
        times = {"pva": 2, "methylcellulose": 1, "wheatpaste": 4, "hideglue": 6}
        return times.get(self.glue_type, 2) * self.layer_count

    def stats(self) -> Dict:
        return {
            "glue_type": self.glue_type,
            "area_to_cover_cm2": self.area_to_cover_cm2,
            "glue_needed_ml": round(self.glue_needed_ml(), 1),
            "total_cost_usd": round(self.total_cost(), 2),
            "drying_time_hours": self.drying_time_hours(),
            "layers": self.layer_count,
        }

def run():
    acc = AdhesiveCoverageCalculator(glue_type="pva", area_to_cover_cm2=500, glue_thickness_mm=0.15, layer_count=2)
    print(acc.stats())

if __name__ == "__main__":
    run()
