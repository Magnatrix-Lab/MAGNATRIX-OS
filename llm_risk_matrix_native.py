"""Risk Matrix — probability, impact, heatmap, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class RiskMatrix:
    risks: List[Dict] = field(default_factory=list)
    """Each risk: {name, probability (1-5), impact (1-5)}"""

    def score(self, risk: Dict) -> int:
        return risk.get("probability", 0) * risk.get("impact", 0)

    def category(self, risk: Dict) -> str:
        s = self.score(risk)
        if s <= 4: return "low"
        elif s <= 9: return "medium"
        elif s <= 14: return "high"
        return "extreme"

    def heatmap(self) -> List[List[int]]:
        grid = [[0]*5 for _ in range(5)]
        for r in self.risks:
            p = min(4, max(0, r.get("probability", 0) - 1))
            i = min(4, max(0, r.get("impact", 0) - 1))
            grid[p][i] += 1
        return grid

    def prioritized(self) -> List[Dict]:
        return sorted(self.risks, key=lambda r: self.score(r), reverse=True)

    def acceptable(self, threshold: int = 12) -> List[Dict]:
        return [r for r in self.risks if self.score(r) <= threshold]

    def stats(self) -> Dict:
        categories = {}
        for r in self.risks:
            c = self.category(r)
            categories[c] = categories.get(c, 0) + 1
        return {"risks": len(self.risks), "categories": categories, "max_score": max(self.score(r) for r in self.risks) if self.risks else 0}

def run():
    rm = RiskMatrix()
    rm.risks = [
        {"name": "Fire", "probability": 2, "impact": 5},
        {"name": "Theft", "probability": 3, "impact": 3},
        {"name": "Flood", "probability": 1, "impact": 5},
    ]
    print(rm.stats())
    print("Heatmap:", rm.heatmap())
    print("Top:", [r["name"] for r in rm.prioritized()])

if __name__ == "__main__":
    run()
