"""Native stdlib module: Tensile Test Calculator
Calculates tensile properties, elongation, and modulus for polymer testing.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class TensileTestCalculator:
    specimen_type: str
    original_length_mm: float
    original_width_mm: float
    original_thickness_mm: float
    yield_force_n: float
    ultimate_force_n: float
    elongation_at_break_mm: float

    def cross_sectional_area_mm2(self) -> float:
        return self.original_width_mm * self.original_thickness_mm

    def yield_strength_mpa(self) -> float:
        if self.cross_sectional_area_mm2() == 0:
            return 0.0
        return self.yield_force_n / self.cross_sectional_area_mm2()

    def ultimate_tensile_strength_mpa(self) -> float:
        if self.cross_sectional_area_mm2() == 0:
            return 0.0
        return self.ultimate_force_n / self.cross_sectional_area_mm2()

    def elongation_at_break_pct(self) -> float:
        if self.original_length_mm == 0:
            return 0.0
        return (self.elongation_at_break_mm / self.original_length_mm) * 100

    def youngs_modulus_mpa(self, linear_region_force_n: float, linear_region_elongation_mm: float) -> float:
        if self.cross_sectional_area_mm2() == 0 or linear_region_elongation_mm == 0 or self.original_length_mm == 0:
            return 0.0
        stress = linear_region_force_n / self.cross_sectional_area_mm2()
        strain = linear_region_elongation_mm / self.original_length_mm
        return stress / strain

    def toughness_mj_m3(self) -> float:
        return (self.yield_strength_mpa() + self.ultimate_tensile_strength_mpa()) / 2 * self.elongation_at_break_pct() / 100

    def stats(self, linear_force_n: float = 0, linear_elongation_mm: float = 0) -> Dict:
        return {
            "specimen": self.specimen_type,
            "yield_strength_mpa": round(self.yield_strength_mpa(), 1),
            "ultimate_strength_mpa": round(self.ultimate_tensile_strength_mpa(), 1),
            "elongation_pct": round(self.elongation_at_break_pct(), 1),
            "youngs_modulus_mpa": round(self.youngs_modulus_mpa(linear_force_n, linear_elongation_mm), 1) if linear_force_n else None,
            "toughness_mj_m3": round(self.toughness_mj_m3(), 2),
        }

def run():
    ttc = TensileTestCalculator(specimen_type="Dog-bone", original_length_mm=50, original_width_mm=10, original_thickness_mm=4, yield_force_n=800, ultimate_force_n=1200, elongation_at_break_mm=15)
    print(ttc.stats(linear_force_n=400, linear_elongation_mm=2))

if __name__ == "__main__":
    run()
