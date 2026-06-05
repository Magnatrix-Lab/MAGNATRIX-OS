"""Underwriting Engine — scoring, declination, rating factors, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class UnderwritingEngine:
    factors: Dict[str, float] = field(default_factory=dict)
    """factor -> weight"""
    scores: Dict[str, float] = field(default_factory=dict)
    """factor -> applicant score"""
    min_acceptable: float = 0.6

    def add_factor(self, name: str, weight: float, score: float):
        self.factors[name] = weight
        self.scores[name] = score

    def weighted_score(self) -> float:
        total_weight = sum(self.factors.values())
        if total_weight == 0:
            return 0.0
        return sum(self.scores.get(f, 0) * w for f, w in self.factors.items()) / total_weight

    def approve(self) -> bool:
        return self.weighted_score() >= self.min_acceptable

    def rate_class(self) -> str:
        s = self.weighted_score()
        if s >= 0.9: return "preferred"
        elif s >= 0.75: return "standard"
        elif s >= 0.6: return "substandard"
        return "decline"

    def loading_pct(self) -> float:
        s = self.weighted_score()
        if s >= 0.9: return 0.0
        elif s >= 0.75: return 0.1
        elif s >= 0.6: return 0.25
        return 0.5

    def stats(self) -> Dict:
        return {"score": round(self.weighted_score(), 3), "approved": self.approve(), "class": self.rate_class()}

def run():
    ue = UnderwritingEngine()
    ue.add_factor("age", 0.3, 0.8)
    ue.add_factor("health", 0.4, 0.7)
    ue.add_factor("occupation", 0.2, 0.9)
    ue.add_factor("credit", 0.1, 0.85)
    print(ue.stats())
    print("Loading:", ue.loading_pct())

if __name__ == "__main__":
    run()
