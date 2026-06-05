"""Native stdlib module: Finish Coverage Calculator
Calculates stain, varnish, oil, and paint coverage for wood projects.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FinishCoverageCalculator:
    finish_type: str  # oil, varnish, lacquer, paint, stain, wax
    surface_area_sqft: float
    coats: int = 1
    wood_porosity: str = "medium"  # low, medium, high

    _COVERAGE_SQFT_PER_GAL = {
        "oil": 400, "varnish": 350, "lacquer": 300, "paint": 250, "stain": 200, "wax": 500,
    }

    _POROSITY_FACTOR = {"low": 1.0, "medium": 1.2, "high": 1.5}

    def coverage_per_gal(self) -> float:
        base = self._COVERAGE_SQFT_PER_GAL.get(self.finish_type, 300)
        return base / self._POROSITY_FACTOR.get(self.wood_porosity, 1.2)

    def gallons_needed(self) -> float:
        if self.coverage_per_gal() == 0:
            return 0
        return (self.surface_area_sqft * self.coats) / self.coverage_per_gal()

    def quarts_needed(self) -> float:
        return self.gallons_needed() * 4

    def cost(self, price_per_gallon: float) -> float:
        return self.gallons_needed() * price_per_gallon

    def drying_time_hours(self) -> float:
        times = {"oil": 24, "varnish": 8, "lacquer": 2, "paint": 4, "stain": 2, "wax": 1}
        return times.get(self.finish_type, 4) * self.coats

    def stats(self, price_per_gallon: float = 40.0) -> Dict:
        return {
            "finish_type": self.finish_type,
            "surface_area_sqft": self.surface_area_sqft,
            "coats": self.coats,
            "gallons_needed": round(self.gallons_needed(), 2),
            "quarts_needed": round(self.quarts_needed(), 2),
            "cost_usd": round(self.cost(price_per_gallon), 2),
            "drying_time_hours": self.drying_time_hours(),
        }

def run():
    fcc = FinishCoverageCalculator(finish_type="varnish", surface_area_sqft=50, coats=2, wood_porosity="high")
    print(fcc.stats(price_per_gallon=35))

if __name__ == "__main__":
    run()
