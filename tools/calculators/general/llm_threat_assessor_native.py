"""Threat Assessor — probability, severity, risk matrix, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Threat:
    name: str
    probability: float
    severity: float
    mitigations: int = 0

class ThreatAssessor:
    def __init__(self):
        self.threats: List[Threat] = []

    def add_threat(self, t: Threat):
        self.threats.append(t)

    def risk_score(self, t: Threat) -> float:
        return t.probability * t.severity * (1 - min(1, t.mitigations * 0.2))

    def risk_level(self, score: float) -> str:
        if score < 3: return "low"
        elif score < 6: return "medium"
        elif score < 9: return "high"
        return "critical"

    def prioritized(self) -> List[Threat]:
        return sorted(self.threats, key=lambda t: self.risk_score(t), reverse=True)

    def matrix(self) -> Dict[Tuple[str, str], List[str]]:
        matrix = {}
        prob_levels = ["low", "medium", "high"]
        sev_levels = ["low", "medium", "high"]
        for p in prob_levels:
            for s in sev_levels:
                matrix[(p, s)] = []
        for t in self.threats:
            p = "low" if t.probability < 0.3 else "medium" if t.probability < 0.7 else "high"
            s = "low" if t.severity < 3 else "medium" if t.severity < 7 else "high"
            matrix[(p, s)].append(t.name)
        return matrix

    def stats(self) -> Dict:
        return {"threats": len(self.threats), "avg_risk": sum(self.risk_score(t) for t in self.threats) / len(self.threats) if self.threats else 0}

def run():
    ta = ThreatAssessor()
    ta.add_threat(Threat("Cyber", 0.7, 8, 2))
    ta.add_threat(Threat("Physical", 0.3, 9, 1))
    ta.add_threat(Threat("Insider", 0.2, 7, 0))
    print(ta.stats())
    print("Top threat:", ta.prioritized()[0].name)

if __name__ == "__main__":
    run()
