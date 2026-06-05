"""Native stdlib module: Armor Penetration Calculator
Estimates armor penetration probability by projectile and armor specs.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class ArmorPenetrationCalculator:
    projectile_diameter_mm: float
    projectile_velocity_m_s: float
    projectile_mass_g: float
    armor_thickness_mm: float
    armor_hardness_hb: float = 500
    projectile_hardness_hb: float = 800

    def sectional_density_kg_m2(self) -> float:
        area_m2 = math.pi * ((self.projectile_diameter_mm / 2000) ** 2)
        mass_kg = self.projectile_mass_g / 1000
        if area_m2 == 0:
            return 0.0
        return mass_kg / area_m2

    def penetration_estimate_mm(self) -> float:
        sd = self.sectional_density_kg_m2()
        velocity_factor = (self.projectile_velocity_m_s / 1000) ** 1.5
        hardness_ratio = self.projectile_hardness_hb / max(1, self.armor_hardness_hb)
        return sd * velocity_factor * hardness_ratio * 2

    def penetration_probability(self) -> float:
        if self.penetration_estimate_mm() >= self.armor_thickness_mm * 1.2:
            return 0.95
        elif self.penetration_estimate_mm() >= self.armor_thickness_mm:
            return 0.7
        elif self.penetration_estimate_mm() >= self.armor_thickness_mm * 0.8:
            return 0.3
        return 0.05

    def armor_quality_factor(self) -> float:
        if self.armor_thickness_mm == 0:
            return 0.0
        return (self.armor_hardness_hb * self.armor_thickness_mm) / 1000

    def stats(self) -> Dict:
        import math
        return {
            "projectile_diameter_mm": self.projectile_diameter_mm,
            "projectile_velocity_m_s": self.projectile_velocity_m_s,
            "armor_thickness_mm": self.armor_thickness_mm,
            "sectional_density": round(self.sectional_density_kg_m2(), 2),
            "penetration_estimate_mm": round(self.penetration_estimate_mm(), 1),
            "penetration_probability": round(self.penetration_probability(), 2),
            "armor_quality": round(self.armor_quality_factor(), 2),
        }

def run():
    apc = ArmorPenetrationCalculator(projectile_diameter_mm=20, projectile_velocity_m_s=1200, projectile_mass_g=150, armor_thickness_mm=50, armor_hardness_hb=500, projectile_hardness_hb=800)
    print(apc.stats())

if __name__ == "__main__":
    run()
