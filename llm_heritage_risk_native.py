"""Heritage Risk Calculator — threats, vulnerability, significance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class HeritageRisk:
    threats: List[str] = field(default_factory=list)
    vulnerability: float = 0.5
    significance: float = 0.8
    mitigation: float = 0.3

    def threat_score(self) -> float:
        weights = {"flood": 0.8, "fire": 0.9, "earthquake": 0.85, "theft": 0.6, "vandalism": 0.5, "deterioration": 0.4, "war": 1.0}
        return sum(weights.get(t, 0.5) for t in self.threats) / max(1, len(self.threats))

    def risk_score(self) -> float:
        return self.threat_score() * self.vulnerability * self.significance * (1 - self.mitigation)

    def risk_level(self) -> str:
        s = self.risk_score()
        if s < 0.1: return "negligible"
        elif s < 0.3: return "low"
        elif s < 0.5: return "medium"
        elif s < 0.7: return "high"
        return "extreme"

    def priority_action(self) -> str:
        level = self.risk_level()
        if level in ["high", "extreme"]:
            return "immediate intervention"
        elif level == "medium":
            return "planned conservation"
        return "routine monitoring"

    def stats(self) -> Dict:
        return {"risk_score": round(self.risk_score(), 3), "level": self.risk_level(), "action": self.priority_action()}

def run():
    hr = HeritageRisk(threats=["fire", "flood"], vulnerability=0.7, significance=0.9, mitigation=0.2)
    print(hr.stats())

if __name__ == "__main__":
    run()
