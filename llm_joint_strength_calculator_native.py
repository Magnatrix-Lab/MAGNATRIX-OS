"""Native stdlib module: Joint Strength Calculator
Calculates joint strength, glue surface area, and mechanical advantage.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class JointStrengthCalculator:
    joint_type: str  # butt, lap, mortise_tenon, dovetail, box, miter, dowel
    glue_surface_area_in2: float
    wood_species_strength_psi: float = 10000.0
    fastener_count: int = 0

    _GLUE_STRENGTH_PSI = {
        "butt": 200, "lap": 250, "mortise_tenon": 300,
        "dovetail": 350, "box": 280, "miter": 180, "dowel": 220,
    }

    _MECHANICAL_FACTOR = {
        "butt": 1.0, "lap": 1.5, "mortise_tenon": 2.0,
        "dovetail": 2.5, "box": 1.8, "miter": 1.2, "dowel": 1.3,
    }

    def glue_strength_psi(self) -> float:
        return self._GLUE_STRENGTH_PSI.get(self.joint_type, 200)

    def mechanical_factor(self) -> float:
        return self._MECHANICAL_FACTOR.get(self.joint_type, 1.0)

    def joint_strength_lbs(self) -> float:
        glue = self.glue_surface_area_in2 * self.glue_strength_psi()
        mechanical = self.glue_surface_area_in2 * self.wood_species_strength_psi * 0.1 * self.mechanical_factor()
        fastener_bonus = self.fastener_count * 50
        return glue + mechanical + fastener_bonus

    def glue_only_strength_lbs(self) -> float:
        return self.glue_surface_area_in2 * self.glue_strength_psi()

    def strength_per_square_inch(self) -> float:
        if self.glue_surface_area_in2 == 0:
            return 0
        return self.joint_strength_lbs() / self.glue_surface_area_in2

    def stats(self) -> Dict:
        return {
            "joint_type": self.joint_type,
            "glue_surface_area_in2": self.glue_surface_area_in2,
            "joint_strength_lbs": round(self.joint_strength_lbs(), 1),
            "glue_only_strength_lbs": round(self.glue_only_strength_lbs(), 1),
            "strength_per_in2": round(self.strength_per_square_inch(), 1),
            "fastener_count": self.fastener_count,
        }

def run():
    jsc = JointStrengthCalculator(joint_type="dovetail", glue_surface_area_in2=12, wood_species_strength_psi=15000, fastener_count=0)
    print(jsc.stats())

if __name__ == "__main__":
    run()
