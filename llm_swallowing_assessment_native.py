"""Native stdlib module: Swallowing Assessment Calculator
Calculates swallowing risk scores and aspiration probability.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Consistency(Enum):
    THIN_LIQUID = "thin_liquid"
    NECTAR = "nectar"
    HONEY = "honey"
    PUDDING = "pudding"
    SOLID = "solid"

@dataclass
class SwallowingTrial:
    consistency: Consistency
    attempts: int
    successful: int
    coughing: bool
    voice_change: bool

@dataclass
class SwallowingAssessmentCalculator:
    patient_name: str
    trials: List[SwallowingTrial] = field(default_factory=list)
    conscious_level: int = 5  # 1-5, 5 = alert
    prior_stroke: bool = False
    tracheostomy: bool = False

    def success_rate_pct(self) -> float:
        total = sum(t.attempts for t in self.trials)
        if total == 0:
            return 0.0
        successful = sum(t.successful for t in self.trials)
        return (successful / total) * 100

    def aspiration_signs(self) -> int:
        return sum(1 for t in self.trials if t.coughing or t.voice_change)

    def aspiration_risk_score(self) -> int:
        score = 0
        if self.success_rate_pct() < 50:
            score += 3
        elif self.success_rate_pct() < 80:
            score += 1
        if self.aspiration_signs() > 0:
            score += 2
        if self.conscious_level < 3:
            score += 2
        if self.prior_stroke:
            score += 1
        if self.tracheostomy:
            score += 1
        return min(10, score)

    def diet_recommendation(self) -> str:
        risk = self.aspiration_risk_score()
        if risk >= 7:
            return "nil_by_mouth_or_ngt"
        elif risk >= 5:
            return "pudding_consistency_only"
        elif risk >= 3:
            return "honey_consistency_with_supervision"
        elif risk >= 1:
            return "nectar_thick_with_cautions"
        return "regular_diet_with_monitoring"

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "trials": len(self.trials),
            "success_rate_pct": round(self.success_rate_pct(), 1),
            "aspiration_signs": self.aspiration_signs(),
            "risk_score": self.aspiration_risk_score(),
            "diet_recommendation": self.diet_recommendation(),
        }

def run():
    sac = SwallowingAssessmentCalculator(
        patient_name="Patient-X",
        conscious_level=4,
        prior_stroke=True,
        tracheostomy=False,
        trials=[
            SwallowingTrial(Consistency.THIN_LIQUID, 3, 1, True, True),
            SwallowingTrial(Consistency.NECTAR, 3, 2, True, False),
            SwallowingTrial(Consistency.HONEY, 3, 3, False, False),
        ]
    )
    print(sac.stats())

if __name__ == "__main__":
    run()
