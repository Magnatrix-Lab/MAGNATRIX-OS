"""Native stdlib module: Map Scale Calculator
Converts between map scales, ground distances, and area representations.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class MapScaleCalculator:
    scale_denominator: int
    map_distance_cm: float

    def ground_distance_m(self) -> float:
        return (self.map_distance_cm * self.scale_denominator) / 100

    def ground_distance_km(self) -> float:
        return self.ground_distance_m() / 1000

    def map_area_cm2(self, ground_area_m2: float) -> float:
        if self.scale_denominator == 0:
            return 0.0
        scale_factor = self.scale_denominator / 100
        return ground_area_m2 / (scale_factor ** 2)

    def representative_fraction(self) -> str:
        return f"1:{self.scale_denominator}"

    def scale_category(self) -> str:
        if self.scale_denominator <= 25000:
            return "large_scale"
        elif self.scale_denominator <= 1000000:
            return "medium_scale"
        return "small_scale"

    def stats(self, ground_area_m2: float = 0) -> Dict:
        return {
            "scale": self.representative_fraction(),
            "scale_category": self.scale_category(),
            "map_distance_cm": self.map_distance_cm,
            "ground_distance_m": round(self.ground_distance_m(), 2),
            "ground_distance_km": round(self.ground_distance_km(), 4),
            "map_area_cm2": round(self.map_area_cm2(ground_area_m2), 2) if ground_area_m2 else None,
        }

def run():
    msc = MapScaleCalculator(scale_denominator=50000, map_distance_cm=10)
    print(msc.stats(ground_area_m2=1000000))

if __name__ == "__main__":
    run()
