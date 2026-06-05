"""Oral Risk Assessor — caries, gum disease, oral cancer, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class OralRiskAssessor:
    sugar_frequency: int = 3
    brushing_frequency: int = 1
    flossing: bool = False
    smoking: bool = False
    alcohol_units: int = 0
    family_history: bool = False
    age: int = 30

    def caries_risk(self) -> float:
        risk = 0.0
        risk += self.sugar_frequency * 0.05
        risk += max(0, (2 - self.brushing_frequency)) * 0.1
        if not self.flossing:
            risk += 0.1
        if self.smoking:
            risk += 0.15
        return min(1.0, risk)

    def gum_disease_risk(self) -> float:
        risk = 0.0
        if not self.flossing:
            risk += 0.3
        if self.smoking:
            risk += 0.3
        risk += max(0, (2 - self.brushing_frequency)) * 0.1
        return min(1.0, risk)

    def oral_cancer_risk(self) -> float:
        risk = 0.0
        if self.smoking:
            risk += 0.2
        if self.alcohol_units > 14:
            risk += 0.15
        if self.family_history:
            risk += 0.1
        if self.age > 50:
            risk += 0.1
        return min(1.0, risk)

    def overall_risk(self) -> str:
        max_risk = max(self.caries_risk(), self.gum_disease_risk(), self.oral_cancer_risk())
        if max_risk >= 0.5: return "high"
        elif max_risk >= 0.3: return "moderate"
        return "low"

    def recommendations(self) -> List[str]:
        recs = []
        if self.brushing_frequency < 2:
            recs.append("brush twice daily")
        if not self.flossing:
            recs.append("floss daily")
        if self.sugar_frequency > 2:
            recs.append("reduce sugar frequency")
        if self.smoking:
            recs.append("quit smoking")
        return recs

    def stats(self) -> Dict:
        return {
            "caries_risk": round(self.caries_risk(), 2),
            "gum_risk": round(self.gum_disease_risk(), 2),
            "cancer_risk": round(self.oral_cancer_risk(), 2),
            "overall": self.overall_risk(),
            "recommendations": self.recommendations()
        }

def run():
    ora = OralRiskAssessor(sugar_frequency=5, brushing_frequency=1, flossing=False, smoking=True, alcohol_units=20, age=55)
    print(ora.stats())

if __name__ == "__main__":
    run()
