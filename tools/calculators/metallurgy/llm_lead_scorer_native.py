"""Lead Scorer — BANT, engagement, fit scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class LeadScoreDimension(Enum):
    BUDGET = auto()
    AUTHORITY = auto()
    NEED = auto()
    TIMING = auto()
    ENGAGEMENT = auto()
    FIT = auto()

class LeadScorer:
    def __init__(self):
        self.weights = {
            "BUDGET": 0.2, "AUTHORITY": 0.2, "NEED": 0.2,
            "TIMING": 0.15, "ENGAGEMENT": 0.15, "FIT": 0.1,
        }
        self.leads: Dict[str, Dict] = {}

    def score_lead(self, lead_id: str, scores: Dict[str, float]) -> float:
        total = 0.0
        for dim, val in scores.items():
            total += val * self.weights.get(dim, 0)
        self.leads[lead_id] = scores
        return total * 100

    def rank(self) -> List[Tuple[str, float]]:
        ranked = []
        for lead_id, scores in self.leads.items():
            total = sum(val * self.weights.get(dim, 0) for dim, val in scores.items()) * 100
            ranked.append((lead_id, total))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def hot_leads(self, threshold: float = 70) -> List[str]:
        return [lid for lid, score in self.rank() if score >= threshold]

    def stats(self) -> Dict:
        return {"leads": len(self.leads), "dimensions": len(self.weights)}

def run():
    ls = LeadScorer()
    ls.score_lead("L1", {"BUDGET": 0.9, "AUTHORITY": 0.8, "NEED": 0.9, "TIMING": 0.7, "ENGAGEMENT": 0.8, "FIT": 0.9})
    ls.score_lead("L2", {"BUDGET": 0.3, "AUTHORITY": 0.2, "NEED": 0.5, "TIMING": 0.1, "ENGAGEMENT": 0.2, "FIT": 0.4})
    print(ls.rank())
    print(ls.hot_leads(70))
    print(ls.stats())

if __name__ == "__main__":
    run()
