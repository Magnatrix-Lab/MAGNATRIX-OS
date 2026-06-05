"""Rock Mechanics — RMR, Q-system, stress, stability, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class RockMechanics:
    rmr_score: float = 0.0
    q_value: float = 0.0
    ucs_mpa: float = 0.0
    joint_spacing: float = 0.0

    def rmr_class(self) -> str:
        if self.rmr_score >= 81: return "I - Very good"
        elif self.rmr_score >= 61: return "II - Good"
        elif self.rmr_score >= 41: return "III - Fair"
        elif self.rmr_score >= 21: return "IV - Poor"
        return "V - Very poor"

    def q_support(self) -> str:
        if self.q_value >= 400: return "no support"
        elif self.q_value >= 100: return "spot bolting"
        elif self.q_value >= 10: return "systematic bolting"
        elif self.q_value >= 1: return "systematic bolting + shotcrete"
        elif self.q_value >= 0.1: return "heavy support"
        return "very heavy support"

    def stand_up_time(self) -> float:
        if self.rmr_score >= 80: return 10.0
        elif self.rmr_score >= 60: return 1.0
        elif self.rmr_score >= 40: return 0.1
        elif self.rmr_score >= 20: return 0.01
        return 0.0

    def stability_factor(self) -> float:
        return self.rmr_score / 100

    def stats(self) -> Dict:
        return {"rmr_class": self.rmr_class(), "q_support": self.q_support(), "stand_up": self.stand_up_time(), "stability": round(self.stability_factor(), 2)}

def run():
    rm = RockMechanics(rmr_score=65, q_value=25, ucs_mpa=80, joint_spacing=0.5)
    print(rm.stats())

if __name__ == "__main__":
    run()
