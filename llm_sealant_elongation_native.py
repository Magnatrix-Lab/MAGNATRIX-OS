"""Sealant Elongation Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SealantElongation:
    original_length_mm: float
    stretched_length_mm: float
    sealant_type: str = "silicone"
    joint_width_mm: float = 10.0

    def elongation_percent(self) -> float:
        if self.original_length_mm <= 0:
            return 0.0
        return round((self.stretched_length_mm - self.original_length_mm) / self.original_length_mm * 100, 2)

    def max_elongation_percent(self) -> float:
        elongations = {"silicone": 500, "pu": 400, "acrylic": 150, "butyl": 50, "polysulfide": 250}
        return elongations.get(self.sealant_type, 200)

    def elongation_utilization(self) -> float:
        max_el = self.max_elongation_percent()
        if max_el <= 0:
            return 0.0
        return round(self.elongation_percent() / max_el * 100, 2)

    def joint_movement_mm(self) -> float:
        return round(self.joint_width_mm * self.elongation_percent() / 100.0, 2)

    def modulus_at_100_percent(self) -> float:
        moduli = {"silicone": 0.4, "pu": 0.6, "acrylic": 1.0, "butyl": 1.5, "polysulfide": 0.5}
        return moduli.get(self.sealant_type, 0.5)

    def stress_at_elongation_mpa(self) -> float:
        return round(self.modulus_at_100_percent() * self.elongation_percent() / 100.0, 3)

    def stats(self) -> Dict[str, float]:
        return {
            "elongation_percent": self.elongation_percent(),
            "max_elongation_percent": self.max_elongation_percent(),
            "utilization_percent": self.elongation_utilization(),
        }

    def run(self):
        print("=" * 60)
        print("SEALANT ELONGATION CALCULATOR")
        print("=" * 60)
        seal = SealantElongation(
            original_length_mm=100, stretched_length_mm=350,
            sealant_type="silicone", joint_width_mm=15
        )
        print(f"Original: {seal.original_length_mm} mm")
        print(f"Stretched: {seal.stretched_length_mm} mm")
        print(f"Elongation: {seal.elongation_percent():.2f}%")
        print(f"Max elongation: {seal.max_elongation_percent()}%")
        print(f"Utilization: {seal.elongation_utilization():.2f}%")
        print(f"Joint movement: {seal.joint_movement_mm():.2f} mm")
        print(f"Stress: {seal.stress_at_elongation_mpa():.3f} MPa")
        print(f"Stats: {seal.stats()}")

if __name__ == "__main__":
    SealantElongation(0, 0).run()
