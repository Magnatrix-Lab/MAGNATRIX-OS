"""Native stdlib module: Coffee Grind Size Calculator
Calculates grind size, surface area, and extraction time estimates.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import math

@dataclass
class CoffeeGrindSizeCalculator:
    grind_setting_microns: float
    dose_g: float
    brew_method: str = "drip"  # espresso, drip, pour_over, french_press, cold_brew

    _RECOMMENDED_MICRONS = {
        "espresso": 250, "drip": 600, "pour_over": 550, "french_press": 900, "cold_brew": 800,
    }

    def particle_surface_area_mm2(self) -> float:
        r = self.grind_setting_microns / 2000
        return 4 * math.pi * r ** 2

    def estimated_particle_count(self) -> float:
        if self.grind_setting_microns == 0:
            return 0
        particle_volume_mm3 = (4 / 3) * math.pi * (self.grind_setting_microns / 2000) ** 3
        bean_density = 0.4
        total_volume_mm3 = self.dose_g / bean_density
        return total_volume_mm3 / particle_volume_mm3

    def total_surface_area_mm2(self) -> float:
        return self.particle_surface_area_mm2() * self.estimated_particle_count()

    def extraction_time_estimate_s(self) -> float:
        bases = {"espresso": 25, "drip": 180, "pour_over": 150, "french_press": 240, "cold_brew": 720}
        base = bases.get(self.brew_method, 180)
        factor = 250 / self.grind_setting_microns if self.grind_setting_microns else 1
        return base * factor

    def grind_match_score(self) -> float:
        recommended = self._RECOMMENDED_MICRONS.get(self.brew_method, 600)
        diff = abs(self.grind_setting_microns - recommended)
        return max(0, 100 - diff * 0.2)

    def grind_category(self) -> str:
        m = self.grind_setting_microns
        if m < 200:
            return "turkish"
        elif m < 300:
            return "espresso"
        elif m < 500:
            return "fine"
        elif m < 700:
            return "medium"
        elif m < 1000:
            return "medium_coarse"
        elif m < 1500:
            return "coarse"
        return "extra_coarse"

    def stats(self) -> Dict:
        return {
            "grind_setting_microns": self.grind_setting_microns,
            "brew_method": self.brew_method,
            "grind_category": self.grind_category(),
            "recommended_microns": self._RECOMMENDED_MICRONS.get(self.brew_method, 600),
            "grind_match_score": round(self.grind_match_score(), 1),
            "estimated_particle_count": round(self.estimated_particle_count(), 0),
            "extraction_time_estimate_s": round(self.extraction_time_estimate_s(), 0),
        }

def run():
    cgsc = CoffeeGrindSizeCalculator(grind_setting_microns=300, dose_g=18, brew_method="espresso")
    print(cgsc.stats())

if __name__ == "__main__":
    run()
