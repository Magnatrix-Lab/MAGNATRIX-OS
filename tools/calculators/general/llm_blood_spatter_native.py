"""Native stdlib module: Blood Spatter Analyzer
Analyzes blood spatter patterns to determine impact angle and origin.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

@dataclass
class BloodStain:
    stain_id: str
    width_mm: float
    length_mm: float
    x_cm: float
    y_cm: float
    z_cm: float

@dataclass
class BloodSpatterAnalyzer:
    case_id: str
    stains: List[BloodStain] = field(default_factory=list)

    def impact_angle_deg(self, stain: BloodStain) -> float:
        if stain.length_mm == 0:
            return 0.0
        return math.degrees(math.asin(stain.width_mm / stain.length_mm))

    def area_of_origin(self, stains: List[BloodStain] = None) -> Tuple[float, float, float]:
        if stains is None:
            stains = self.stains
        if len(stains) < 2:
            return (0.0, 0.0, 0.0)
        x = sum(s.x_cm for s in stains) / len(stains)
        y = sum(s.y_cm for s in stains) / len(stains)
        z = sum(s.z_cm for s in stains) / len(stains)
        return (round(x, 1), round(y, 1), round(z, 1))

    def pattern_type(self) -> str:
        if len(self.stains) < 3:
            return "insufficient_data"
        avg_angle = sum(self.impact_angle_deg(s) for s in self.stains) / len(self.stains)
        if avg_angle > 70:
            return "impact_spatter"
        elif avg_angle > 30:
            return "medium_velocity"
        else:
            return "low_velocity"

    def convergence_point(self) -> Tuple[float, float]:
        if len(self.stains) < 2:
            return (0.0, 0.0)
        x = sum(s.x_cm for s in self.stains) / len(self.stains)
        y = sum(s.y_cm for s in self.stains) / len(self.stains)
        return (round(x, 1), round(y, 1))

    def stats(self) -> Dict:
        return {
            "case_id": self.case_id,
            "stains": len(self.stains),
            "pattern_type": self.pattern_type(),
            "area_of_origin": self.area_of_origin(),
            "convergence_point": self.convergence_point(),
            "avg_impact_angle": round(sum(self.impact_angle_deg(s) for s in self.stains) / max(1, len(self.stains)), 1),
        }

def run():
    bsa = BloodSpatterAnalyzer(
        case_id="CASE-2024-001",
        stains=[
            BloodStain("S1", 3, 8, 50, 30, 120),
            BloodStain("S2", 2.5, 7, 52, 32, 118),
            BloodStain("S3", 3.2, 9, 48, 28, 122),
            BloodStain("S4", 2.8, 7.5, 51, 31, 119),
        ]
    )
    print(bsa.stats())

if __name__ == "__main__":
    run()
