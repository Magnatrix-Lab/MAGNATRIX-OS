"""Native stdlib module: Blasting Calculator
Calculates blast parameters, powder factors, and fragmentation for mining.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ExplosiveType(Enum):
    ANFO = "anfo"
    EMULSION = "emulsion"
    DYNAMITE = "dynamite"
    WATERGEL = "watergel"

@dataclass
class BlastingCalculator:
    bench_height_m: float
    hole_diameter_mm: float
    hole_depth_m: float
    spacing_m: float
    burden_m: float
    explosive_type: ExplosiveType
    explosive_density_g_cm3: float

    def hole_volume_m3(self) -> float:
        radius_m = (self.hole_diameter_mm / 1000) / 2
        return math.pi * (radius_m ** 2) * self.hole_depth_m

    def explosive_mass_kg(self) -> float:
        return self.hole_volume_m3() * (self.explosive_density_g_cm3 * 1000)

    def powder_factor_kg_m3(self) -> float:
        rock_volume = self.burden_m * self.spacing_m * self.bench_height_m
        if rock_volume == 0:
            return 0.0
        return self.explosive_mass_kg() / rock_volume

    def stemming_length_m(self) -> float:
        return self.burden_m * 0.7

    def subdrill_m(self) -> float:
        return self.hole_diameter_mm / 1000 * 10

    def fragmentation_estimate_cm(self) -> float:
        if self.powder_factor_kg_m3() == 0:
            return 0.0
        return 50 / (self.powder_factor_kg_m3() ** 0.5)

    def vibration_prediction_mm_s(self, distance_m: float) -> float:
        if distance_m == 0:
            return 0.0
        return 1000 * (self.explosive_mass_kg() ** 0.5) / distance_m

    def stats(self, distance_m: float = 500) -> Dict:
        return {
            "hole_volume_m3": round(self.hole_volume_m3(), 3),
            "explosive_mass_kg": round(self.explosive_mass_kg(), 1),
            "powder_factor_kg_m3": round(self.powder_factor_kg_m3(), 2),
            "stemming_length_m": round(self.stemming_length_m(), 1),
            "subdrill_m": round(self.subdrill_m(), 1),
            "fragmentation_cm": round(self.fragmentation_estimate_cm(), 1),
            "vibration_mm_s": round(self.vibration_prediction_mm_s(distance_m), 2),
        }

def run():
    import math
    bc = BlastingCalculator(bench_height_m=15, hole_diameter_mm=150, hole_depth_m=17, spacing_m=5, burden_m=4.5, explosive_type=ExplosiveType.ANFO, explosive_density_g_cm3=0.85)
    print(bc.stats(distance_m=800))

if __name__ == "__main__":
    run()
