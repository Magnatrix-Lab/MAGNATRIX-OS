"""Underwriting Scorer — risk score, declination, modification, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class UnderwritingScorer:
    age: int = 30
    bmi: float = 22.0
    smoker: bool = False
    medical_history: List[str] = field(default_factory=list)
    occupation_risk: int = 1

    def base_score(self) -> float:
        score = 100
        if self.age > 50: score -= 20
        elif self.age > 40: score -= 10
        if self.bmi > 30: score -= 15
        elif self.bmi > 25: score -= 5
        if self.smoker: score -= 25
        score -= len(self.medical_history) * 5
        score -= self.occupation_risk * 10
        return max(0, score)

    def decision(self) -> str:
        s = self.base_score()
        if s >= 80: return "standard"
        elif s >= 60: return "rated"
        elif s >= 40: return "modified"
        return "decline"

    def loading_pct(self) -> float:
        s = self.base_score()
        if s >= 80: return 0
        elif s >= 60: return 0.25
        elif s >= 40: return 0.5
        return 1.0

    def modification(self) -> List[str]:
        mods = []
        if self.smoker:
            mods.append("smoker premium")
        if self.bmi > 30:
            mods.append("weight exclusion period")
        if self.occupation_risk > 2:
            mods.append("accident exclusion")
        return mods

    def stats(self) -> Dict:
        return {"score": self.base_score(), "decision": self.decision(), "loading": self.loading_pct()}

def run():
    us = UnderwritingScorer(age=55, bmi=32, smoker=True, medical_history=["diabetes"], occupation_risk=3)
    print(us.stats())
    print("Modifications:", us.modification())

if __name__ == "__main__":
    run()
