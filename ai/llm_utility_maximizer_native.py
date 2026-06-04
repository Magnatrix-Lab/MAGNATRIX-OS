"""Utility Maximizer - Expected utility for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
from enum import Enum, auto
import math

class RiskProfile(Enum):
    NEUTRAL = auto(); AVERSE = auto(); SEEKING = auto()

@dataclass
class UtilityMaximizer:
    risk_profile: RiskProfile = RiskProfile.NEUTRAL

    def utility(self, value: float) -> float:
        if self.risk_profile == RiskProfile.NEUTRAL: return value
        if self.risk_profile == RiskProfile.AVERSE: return math.log(1 + value) if value > -1 else float('-inf')
        if self.risk_profile == RiskProfile.SEEKING: return value ** 2
        return value

    def expected_utility(self, outcomes: List[Tuple[float, float]]) -> float:
        return sum(prob * self.utility(value) for prob, value in outcomes)

    def choose(self, choices: List[List[Tuple[float, float]]]) -> int:
        return max(range(len(choices)), key=lambda i: self.expected_utility(choices[i]))

    def stats(self, choices: List[List[Tuple[float, float]]]) -> dict:
        utilities = [self.expected_utility(c) for c in choices]
        return {"risk": self.risk_profile.name, "best_choice": self.choose(choices), "utilities": [round(u, 4) for u in utilities]}

def run():
    um = UtilityMaximizer(RiskProfile.AVERSE)
    choices = [
        [(0.5, 100), (0.5, 0)],
        [(0.6, 50), (0.4, 30)]
    ]
    print("Best choice:", um.choose(choices))
    print("Stats:", um.stats(choices))

if __name__ == "__main__": run()
