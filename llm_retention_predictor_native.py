"""Retention Predictor — attrition risk, engagement, tenure, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class RetentionPredictor:
    tenure_months: float = 0.0
    engagement_score: float = 0.0
    last_promotion_months: float = 0.0
    satisfaction: float = 0.0
    market_opportunity: float = 0.0

    def attrition_risk(self) -> float:
        risk = 0.0
        if self.tenure_months < 6:
            risk += 0.3
        elif self.tenure_months > 60:
            risk += 0.15
        risk += max(0, (1 - self.engagement_score)) * 0.3
        risk += max(0, (self.last_promotion_months - 24) / 60) * 0.2
        risk += max(0, (1 - self.satisfaction)) * 0.1
        risk += self.market_opportunity * 0.1
        return min(1.0, risk)

    def risk_level(self) -> str:
        r = self.attrition_risk()
        if r < 0.3: return "low"
        elif r < 0.5: return "moderate"
        elif r < 0.7: return "high"
        return "critical"

    def recommended_actions(self) -> List[str]:
        actions = []
        if self.last_promotion_months > 24:
            actions.append("promotion_discussion")
        if self.engagement_score < 0.6:
            actions.append("engagement_program")
        if self.satisfaction < 0.5:
            actions.append("stay_interview")
        return actions

    def cost_of_replacement(self, salary: float) -> float:
        return salary * 0.5 + 5000

    def stats(self) -> Dict:
        return {
            "attrition_risk": round(self.attrition_risk(), 3),
            "level": self.risk_level(),
            "actions": self.recommended_actions()
        }

def run():
    rp = RetentionPredictor(tenure_months=36, engagement_score=0.5, last_promotion_months=30, satisfaction=0.4, market_opportunity=0.8)
    print(rp.stats())
    print("Replacement cost:", rp.cost_of_replacement(80000))

if __name__ == "__main__":
    run()
