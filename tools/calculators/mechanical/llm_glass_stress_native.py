"""Native stdlib module: Glass Stress Calculator
Calculates thermal stress, annealing schedules, and safety factors for glass.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class GlassType(Enum):
    SODA_LIME = "soda_lime"
    BOROSILICATE = "borosilicate"
    TEMPERED = "tempered"
    LAMINATED = "laminated"
    LEAD_CRYSTAL = "lead_crystal"

@dataclass
class GlassStressCalculator:
    glass_type: GlassType
    thickness_mm: float
    area_m2: float
    temp_gradient_c_mm: float
    support_span_m: float
    load_kpa: float

    def thermal_stress_mpa(self) -> float:
        expansion = {GlassType.SODA_LIME: 9e-6, GlassType.BOROSILICATE: 3.3e-6, GlassType.TEMPERED: 9e-6, GlassType.LAMINATED: 9e-6, GlassType.LEAD_CRYSTAL: 9e-6}
        e_modulus = {GlassType.SODA_LIME: 70, GlassType.BOROSILICATE: 64, GlassType.TEMPERED: 70, GlassType.LAMINATED: 70, GlassType.LEAD_CRYSTAL: 60}
        alpha = expansion.get(self.glass_type, 9e-6)
        e = e_modulus.get(self.glass_type, 70)
        return e * 1e9 * alpha * self.temp_gradient_c_mm * (self.thickness_mm / 1000) / (1 - 0.22)

    def bending_stress_mpa(self) -> float:
        if self.support_span_m == 0:
            return 0.0
        t_m = self.thickness_mm / 1000
        return (1.5 * self.load_kpa * 1000 * (self.support_span_m ** 2)) / (t_m ** 2)

    def safety_factor(self) -> float:
        strength = {GlassType.SODA_LIME: 45, GlassType.BOROSILICATE: 60, GlassType.TEMPERED: 120, GlassType.LAMINATED: 45, GlassType.LEAD_CRYSTAL: 35}
        max_stress = self.thermal_stress_mpa() + self.bending_stress_mpa()
        if max_stress == 0:
            return 999.0
        return strength.get(self.glass_type, 45) / max_stress

    def annealing_point_c(self) -> float:
        points = {GlassType.SODA_LIME: 540, GlassType.BOROSILICATE: 560, GlassType.TEMPERED: 540, GlassType.LAMINATED: 540, GlassType.LEAD_CRYSTAL: 400}
        return points.get(self.glass_type, 540)

    def strain_point_c(self) -> float:
        return self.annealing_point_c() - 50

    def weight_kg(self) -> float:
        return self.area_m2 * (self.thickness_mm / 1000) * 2500

    def stats(self) -> Dict:
        return {
            "glass_type": self.glass_type.value,
            "thermal_stress_mpa": round(self.thermal_stress_mpa(), 2),
            "bending_stress_mpa": round(self.bending_stress_mpa(), 2),
            "safety_factor": round(self.safety_factor(), 2),
            "annealing_point_c": self.annealing_point_c(),
            "strain_point_c": self.strain_point_c(),
            "weight_kg": round(self.weight_kg(), 1),
        }

def run():
    gsc = GlassStressCalculator(glass_type=GlassType.TEMPERED, thickness_mm=8, area_m2=2, temp_gradient_c_mm=5, support_span_m=1.2, load_kpa=1.5)
    print(gsc.stats())

if __name__ == "__main__":
    run()
