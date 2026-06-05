"""Underwriting Engine — scoring, declination, modification, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class UnderwritingEngine:
    age: int = 30
    health_score: float = 80.0
    credit_score: int = 700
    occupation_risk: int = 1
    smoking: bool = False

    def risk_score(self) -> float:
        score = 0.0
        score += max(0, (self.age - 25) * 0.5)
        score += max(0, (100 - self.health_score) * 0.3)
        score += max(0, (700 - self.credit_score) * 0.01)
        score += self.occupation_risk * 5
        if self.smoking:
            score += 20
        return score

    def decision(self) -> str:
        s = self.risk_score()
        if s > 80: return "decline"
        elif s > 50: return "modified"
        elif s > 30: return "rated"
        return "standard"

    def loading_pct(self) -> float:
        s = self.risk_score()
        if s > 50: return (s - 50) * 2
        return 0.0

    def exclusion_list(self) -> List[str]:
        if self.occupation_risk > 3:
            return ["accidental death", "disability"]
        if self.smoking:
            return ["smoking-related illness"]
        return []

    def stats(self) -> Dict:
        return {"score": round(self.risk_score(), 1), "decision": self.decision(), "loading": round(self.loading_pct(), 1)}

def run():
    ue = UnderwritingEngine(age=55, health_score=60, credit_score=600, occupation_risk=4, smoking=True)
    print(ue.stats())
    print("Exclusions:", ue.exclusion_list())

if __name__ == "__main__":
    run()
