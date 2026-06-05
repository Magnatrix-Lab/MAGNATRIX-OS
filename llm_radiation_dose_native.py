"""Radiation Dose Calculator — exposure, shielding, ALARA, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class RadiationDoseCalculator:
    kvp: float = 70.0
    mas: float = 10.0
    distance_cm: float = 100.0
    exposure_time: float = 0.2

    def exposure(self) -> float:
        return self.kvp * self.mas * 0.001

    def inverse_square_dose(self, target_distance: float) -> float:
        return self.exposure() * (self.distance_cm / target_distance) ** 2 if target_distance > 0 else 0.0

    def shielded_dose(self, thickness_mm: float, hvl_mm: float = 2.0) -> float:
        return self.exposure() * (0.5 ** (thickness_mm / hvl_mm)) if hvl_mm > 0 else self.exposure()

    def lead_equivalent(self, dose_reduction_factor: float = 10.0) -> float:
        return 3.3 * math.log10(dose_reduction_factor) if dose_reduction_factor > 0 else 0.0

    def alara_check(self, annual_limit_msv: float = 20.0, annual_dose: float = 0.0) -> str:
        if annual_dose > annual_limit_msv * 0.75: return "approach limit"
        elif annual_dose > annual_limit_msv * 0.5: return "monitor closely"
        return "within limits"

    def stats(self, target_distance: float = 50.0) -> Dict:
        return {
            "exposure": round(self.exposure(), 3),
            "dose_at_target": round(self.inverse_square_dose(target_distance), 3),
            "shielded_2mm": round(self.shielded_dose(2.0), 3)
        }

def run():
    rdc = RadiationDoseCalculator(kvp=80, mas=15, distance_cm=100)
    print(rdc.stats())
    print("ALARA check:", rdc.alara_check(annual_dose=12))

if __name__ == "__main__":
    run()
