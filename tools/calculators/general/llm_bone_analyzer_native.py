"""Bone Analyzer — measurements, sex estimation, age, stature, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class BoneAnalyzer:
    femur_length: float = 0.0
    humerus_length: float = 0.0
    pelvis_width: float = 0.0
    pubic_symphysis_phase: int = 0

    def stature(self, sex: str = "male") -> float:
        if sex == "male":
            return 2.32 * self.femur_length + 65.53
        return 2.47 * self.femur_length + 54.10

    def sex_estimate(self) -> str:
        if self.pelvis_width > 0:
            if self.pelvis_width > 30:
                return "likely female"
            elif self.pelvis_width < 26:
                return "likely male"
        return "indeterminate"

    def age_estimate(self) -> float:
        if self.pubic_symphysis_phase == 1:
            return 18
        elif self.pubic_symphysis_phase == 2:
            return 25
        elif self.pubic_symphysis_phase == 3:
            return 35
        elif self.pubic_symphysis_phase == 4:
            return 50
        elif self.pubic_symphysis_phase >= 5:
            return 60
        return 0.0

    def stats(self) -> Dict:
        return {"stature": round(self.stature(), 1), "sex": self.sex_estimate(), "age": self.age_estimate()}

def run():
    ba = BoneAnalyzer(femur_length=45, pelvis_width=28, pubic_symphysis_phase=3)
    print(ba.stats())

if __name__ == "__main__":
    run()
