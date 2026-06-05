"""Hazmat Calculator — plume, isolation, ERPG, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class HazmatCalculator:
    chemical: str = ""
    release_rate_kg_s: float = 1.0
    wind_speed: float = 5.0
    stability_class: str = "D"

    def plume_distance(self, concentration_ppm: float, threshold_ppm: float) -> float:
        if concentration_ppm <= 0 or threshold_ppm <= 0:
            return 0.0
        return (concentration_ppm / threshold_ppm) ** 0.5 * 100

    def isolation_zone(self, erpg3: float) -> float:
        return self.plume_distance(self.release_rate_kg_s * 1000, erpg3)

    def protect_action_distance(self, erpg2: float) -> float:
        return self.plume_distance(self.release_rate_kg_s * 1000, erpg2) * 2

    def safe_distance(self, toxicity: str) -> float:
        distances = {"low": 100, "moderate": 300, "high": 800, "extreme": 2000}
        return distances.get(toxicity, 300)

    def downwind_concentration(self, distance_m: float, release_rate: float) -> float:
        if distance_m <= 0:
            return 0.0
        return release_rate / (math.pi * distance_m * self.wind_speed)

    def stats(self) -> Dict:
        return {"chemical": self.chemical, "release_rate": self.release_rate_kg_s, "wind": self.wind_speed}

def run():
    hc = HazmatCalculator("Chlorine", 2.0, 3.0, "C")
    print(hc.stats())
    print("Isolation:", hc.isolation_zone(10))
    print("PAD:", hc.protect_action_distance(3))

if __name__ == "__main__":
    run()
