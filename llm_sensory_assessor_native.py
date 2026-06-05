"""Sensory Assessor -- vision, hearing, touch, balance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class SensoryAssessor:
    visual_acuity: float = 1.0
    hearing_threshold_db: List[float] = field(default_factory=list)
    proprioception_score: float = 10.0
    balance_time_sec: float = 30.0

    def vision_category(self) -> str:
        if self.visual_acuity >= 1.0: return "normal"
        elif self.visual_acuity >= 0.5: return "mild impairment"
        elif self.visual_acuity >= 0.2: return "moderate impairment"
        return "severe impairment"

    def hearing_loss(self) -> float:
        if not self.hearing_threshold_db:
            return 0.0
        avg = sum(self.hearing_threshold_db) / len(self.hearing_threshold_db)
        return max(0, avg - 25)

    def hearing_category(self) -> str:
        loss = self.hearing_loss()
        if loss < 15: return "normal"
        elif loss < 30: return "mild"
        elif loss < 50: return "moderate"
        elif loss < 70: return "severe"
        return "profound"

    def balance_category(self) -> str:
        if self.balance_time_sec >= 30: return "normal"
        elif self.balance_time_sec >= 20: return "mild deficit"
        elif self.balance_time_sec >= 10: return "moderate deficit"
        return "severe deficit"

    def sensory_profile(self) -> Dict:
        return {
            "vision": self.vision_category(),
            "hearing": self.hearing_category(),
            "balance": self.balance_category(),
            "proprioception": "normal" if self.proprioception_score >= 8 else "impaired"
        }

    def stats(self) -> Dict:
        return {"vision": self.vision_category(), "hearing": self.hearing_category(), "balance": self.balance_category()}

def run():
    sa = SensoryAssessor(visual_acuity=0.6, hearing_threshold_db=[30, 35, 40, 45], balance_time_sec=15)
    print(sa.stats())
    print("Profile:", sa.sensory_profile())

if __name__ == "__main__":
    run()
