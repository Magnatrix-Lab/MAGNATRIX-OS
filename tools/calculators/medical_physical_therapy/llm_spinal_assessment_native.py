"""Native stdlib module: Spinal Assessment Calculator
Calculates spinal angles, flexibility, and curvature metrics.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class SpinalAssessmentCalculator:
    patient_name: str
    standing_height_cm: float
    sitting_height_cm: float
    arm_span_cm: float
    trunk_inclination_deg: float
    lumbar_flexion_cm: float
    thoracic_flexion_cm: float

    def sitting_standing_ratio(self) -> float:
        if self.standing_height_cm == 0:
            return 0.0
        return self.sitting_height_cm / self.standing_height_cm

    def arm_span_height_ratio(self) -> float:
        if self.standing_height_cm == 0:
            return 0.0
        return self.arm_span_cm / self.standing_height_cm

    def total_spinal_flexion_cm(self) -> float:
        return self.lumbar_flexion_cm + self.thoracic_flexion_cm

    def schober_index_cm(self) -> float:
        return self.lumbar_flexion_cm

    def spinal_flexibility_pct(self, normal_total_cm: float = 15) -> float:
        if normal_total_cm == 0:
            return 0.0
        return (self.total_spinal_flexion_cm() / normal_total_cm) * 100

    def trunk_inclination_category(self) -> str:
        angle = abs(self.trunk_inclination_deg)
        if angle < 5:
            return "normal"
        elif angle < 15:
            return "mild_forward_inclination"
        elif angle < 30:
            return "moderate_forward_inclination"
        return "severe_forward_inclination"

    def predicted_stature_cm(self) -> float:
        if self.sitting_standing_ratio() > 0.55:
            return self.sitting_height_cm / 0.52
        return self.arm_span_cm

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "standing_height_cm": self.standing_height_cm,
            "sitting_standing_ratio": round(self.sitting_standing_ratio(), 3),
            "arm_span_height_ratio": round(self.arm_span_height_ratio(), 3),
            "total_spinal_flexion_cm": round(self.total_spinal_flexion_cm(), 1),
            "schober_index_cm": round(self.schober_index_cm(), 1),
            "flexibility_pct": round(self.spinal_flexibility_pct(), 1),
            "trunk_inclination": self.trunk_inclination_category(),
        }

def run():
    sac = SpinalAssessmentCalculator(patient_name="Patient-D", standing_height_cm=175, sitting_height_cm=92, arm_span_cm=178, trunk_inclination_deg=8, lumbar_flexion_cm=4, thoracic_flexion_cm=3)
    print(sac.stats())

if __name__ == "__main__":
    run()
