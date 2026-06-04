"""Diagnostic Assistant — symptom scoring, differential, rule-based, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class DiagnosticAssistant:
    symptoms: Dict[str, float] = field(default_factory=dict)
    """symptom -> severity 0-1"""
    rules: Dict[str, List[str]] = field(default_factory=dict)
    """condition -> required symptoms"""

    def add_symptom(self, name: str, severity: float):
        self.symptoms[name] = severity

    def score_condition(self, condition: str) -> float:
        required = self.rules.get(condition, [])
        if not required:
            return 0.0
        scores = [self.symptoms.get(s, 0) for s in required]
        return sum(scores) / len(scores)

    def differential(self, top_n: int = 3) -> List[Tuple[str, float]]:
        scored = [(c, self.score_condition(c)) for c in self.rules]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]

    def add_rule(self, condition: str, symptoms: List[str]):
        self.rules[condition] = symptoms

    def red_flags(self, flags: List[str]) -> List[str]:
        return [f for f in flags if self.symptoms.get(f, 0) > 0.7]

    def stats(self) -> Dict:
        return {"symptoms": len(self.symptoms), "conditions": len(self.rules)}

def run():
    da = DiagnosticAssistant()
    da.add_rule("flu", ["fever", "cough", "fatigue"])
    da.add_rule("cold", ["cough", "sneezing"])
    da.add_symptom("fever", 0.9)
    da.add_symptom("cough", 0.7)
    da.add_symptom("fatigue", 0.6)
    print("Differential:", da.differential())
    print(da.stats())

if __name__ == "__main__":
    run()
