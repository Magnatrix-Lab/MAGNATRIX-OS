"""Rock Mechanics — RMR, Q-system, stress, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class RockMechanics:
    rmr_score: int = 60
    q_value: float = 10.0
    ucs_mpa: float = 100.0
    stress_ratio: float = 0.5

    def rmr_class(self) -> str:
        if self.rmr_score >= 81: return "I (Very Good)"
        elif self.rmr_score >= 61: return "II (Good)"
        elif self.rmr_score >= 41: return "III (Fair)"
        elif self.rmr_score >= 21: return "IV (Poor)"
        return "V (Very Poor)"

    def stand_up_time(self) -> float:
        if self.rmr_score >= 81: return 10 * 365
        elif self.rmr_score >= 61: return 6 * 30
        elif self.rmr_score >= 41: return 7
        elif self.rmr_score >= 21: return 10 / 24
        return 0.5 / 24

    def support_required(self) -> str:
        if self.rmr_score >= 81: return "none"
        elif self.rmr_score >= 61: return "spot bolting"
        elif self.rmr_score >= 41: return "systematic bolting"
        elif self.rmr_score >= 21: return "heavy support"
        return "extensive support"

    def q_support(self) -> float:
        return self.q_value ** 0.5 if self.q_value > 0 else 0.0

    def stress_condition(self) -> str:
        if self.stress_ratio < 0.2: return "low stress"
        elif self.stress_ratio < 0.6: return "medium stress"
        elif self.stress_ratio < 0.8: return "high stress"
        return "very high stress"

    def stats(self) -> Dict:
        return {"rmr_class": self.rmr_class(), "stand_up_time_days": round(self.stand_up_time(), 1), "support": self.support_required(), "stress": self.stress_condition()}

def run():
    rm = RockMechanics(rmr_score=55, q_value=8, stress_ratio=0.4)
    print(rm.stats())

if __name__ == "__main__":
    run()
