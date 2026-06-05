"""Injury Predictor — risk factors, workload, fatigue, history, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class InjuryPredictor:
    workload: float = 0.5
    fatigue: float = 0.5
    prior_injuries: int = 0
    sleep_hours: float = 7.0
    age: int = 25

    def risk_score(self) -> float:
        score = self.workload * 0.3 + self.fatigue * 0.3
        score += min(self.prior_injuries * 0.05, 0.2)
        score += max(0, (7 - self.sleep_hours) / 7) * 0.1
        score += max(0, (self.age - 25) / 50) * 0.1
        return min(1.0, score)

    def risk_level(self) -> str:
        s = self.risk_score()
        if s < 0.3:
            return "low"
        elif s < 0.5:
            return "moderate"
        elif s < 0.7:
            return "high"
        return "critical"

    def recommended_rest(self) -> int:
        s = self.risk_score()
        if s > 0.7:
            return 3
        elif s > 0.5:
            return 2
        elif s > 0.3:
            return 1
        return 0

    def stats(self) -> Dict:
        return {"risk": round(self.risk_score(), 3), "level": self.risk_level(), "rest_days": self.recommended_rest()}

def run():
    ip = InjuryPredictor(workload=0.8, fatigue=0.7, prior_injuries=2, sleep_hours=5, age=32)
    print(ip.stats())

if __name__ == "__main__":
    run()
