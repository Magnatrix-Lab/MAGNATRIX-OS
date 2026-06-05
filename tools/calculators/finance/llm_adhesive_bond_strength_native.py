"""Adhesive Bond Strength Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class AdhesiveBondStrength:
    bond_area_sqm: float
    failure_force_n: float
    adhesive_thickness_mm: float = 0.2
    substrate_type: str = "steel"
    adhesive_type: str = "epoxy"

    def shear_strength_mpa(self) -> float:
        if self.bond_area_sqm <= 0:
            return 0.0
        return round(self.failure_force_n / self.bond_area_sqm / 1e6, 3)

    def tensile_strength_mpa(self) -> float:
        return round(self.shear_strength_mpa() * 1.5, 3)

    def peel_strength_n_per_mm(self) -> float:
        if self.bond_area_sqm <= 0:
            return 0.0
        width_mm = math.sqrt(self.bond_area_sqm) * 1000
        return round(self.failure_force_n / width_mm, 2)

    def theoretical_max_strength_mpa(self) -> float:
        strengths = {"epoxy": 30, "pu": 15, "acrylic": 10, "silicone": 5, "cyanoacrylate": 25}
        return strengths.get(self.adhesive_type, 15)

    def efficiency_percent(self) -> float:
        theoretical = self.theoretical_max_strength_mpa()
        if theoretical <= 0:
            return 0.0
        return round(min(self.shear_strength_mpa() / theoretical * 100, 100), 2)

    def adhesive_volume_ml(self) -> float:
        return round(self.bond_area_sqm * self.adhesive_thickness_mm * 1000, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "shear_strength_mpa": self.shear_strength_mpa(),
            "tensile_strength_mpa": self.tensile_strength_mpa(),
            "efficiency_percent": self.efficiency_percent(),
        }

    def run(self):
        print("=" * 60)
        print("ADHESIVE BOND STRENGTH CALCULATOR")
        print("=" * 60)
        bond = AdhesiveBondStrength(
            bond_area_sqm=0.0025, failure_force_n=5000,
            adhesive_thickness_mm=0.3, substrate_type="aluminum", adhesive_type="epoxy"
        )
        print(f"Bond area: {bond.bond_area_sqm} sqm")
        print(f"Failure force: {bond.failure_force_n} N")
        print(f"Adhesive: {bond.adhesive_type}")
        print(f"Shear strength: {bond.shear_strength_mpa():.3f} MPa")
        print(f"Tensile strength: {bond.tensile_strength_mpa():.3f} MPa")
        print(f"Peel strength: {bond.peel_strength_n_per_mm():.2f} N/mm")
        print(f"Efficiency: {bond.efficiency_percent():.2f}%")
        print(f"Adhesive volume: {bond.adhesive_volume_ml():.2f} ml")
        print(f"Stats: {bond.stats()}")

if __name__ == "__main__":
    AdhesiveBondStrength(0, 0).run()
