"""Vendor Scorer — KPIs, history, risk, rating, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class VendorScorer:
    on_time_delivery: float = 0.0
    quality_score: float = 0.0
    price_competitiveness: float = 0.0
    responsiveness: float = 0.0
    years_in_business: int = 0
    financial_stability: float = 0.0

    def overall(self) -> float:
        return (self.on_time_delivery + self.quality_score + self.price_competitiveness + self.responsiveness) / 4

    def risk_score(self) -> float:
        risk = 0.0
        if self.years_in_business < 3:
            risk += 0.2
        risk += (1 - self.financial_stability) * 0.3
        risk += (1 - self.on_time_delivery) * 0.3
        risk += (1 - self.quality_score) * 0.2
        return min(1.0, risk)

    def tier(self) -> str:
        o = self.overall()
        if o >= 0.9 and self.risk_score() < 0.2:
            return "strategic"
        elif o >= 0.7:
            return "approved"
        elif o >= 0.5:
            return "conditional"
        return "rejected"

    def trend(self, history: List[float]) -> str:
        if len(history) < 2:
            return "stable"
        return "improving" if history[-1] > history[0] else "declining" if history[-1] < history[0] else "stable"

    def stats(self) -> Dict:
        return {"overall": round(self.overall(), 3), "risk": round(self.risk_score(), 3), "tier": self.tier()}

def run():
    vs = VendorScorer(0.95, 0.9, 0.85, 0.8, 10, 0.9)
    print(vs.stats())
    print("Trend:", vs.trend([0.7, 0.75, 0.8, 0.85]))

if __name__ == "__main__":
    run()
