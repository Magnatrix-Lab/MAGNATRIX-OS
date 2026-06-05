"""Risk Matrix — likelihood, impact, heat map, scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class RiskMatrix:
    risks: List[Dict] = field(default_factory=list)
    """Each: {name, likelihood, impact} 1-5"""

    def add_risk(self, name: str, likelihood: int, impact: int):
        self.risks.append({"name": name, "likelihood": likelihood, "impact": impact})

    def score(self, risk: Dict) -> int:
        return risk["likelihood"] * risk["impact"]

    def level(self, score: int) -> str:
        if score <= 4: return "low"
        elif score <= 9: return "medium"
        elif score <= 14: return "high"
        return "critical"

    def heat_map(self) -> List[List[int]]:
        grid = [[0]*5 for _ in range(5)]
        for r in self.risks:
            l = max(0, min(4, r["likelihood"] - 1))
            i = max(0, min(4, r["impact"] - 1))
            grid[l][i] += 1
        return grid

    def prioritized(self) -> List[Dict]:
        return sorted(self.risks, key=lambda r: self.score(r), reverse=True)

    def stats(self) -> Dict:
        scores = [self.score(r) for r in self.risks]
        return {"risks": len(self.risks), "avg_score": sum(scores)/len(scores) if scores else 0, "critical": sum(1 for s in scores if s >= 15)}

def run():
    rm = RiskMatrix()
    rm.add_risk("Fire", 2, 5)
    rm.add_risk("Theft", 3, 3)
    rm.add_risk("Cyber", 4, 4)
    print(rm.stats())
    print("Heat map:", rm.heat_map())
    print("Top:", [(r["name"], rm.score(r)) for r in rm.prioritized()[:3]])

if __name__ == "__main__":
    run()
