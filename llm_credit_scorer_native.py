"""Credit Scorer — FICO-style scoring, default probability, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class CreditTier(Enum):
    EXCELLENT = auto()
    GOOD = auto()
    FAIR = auto()
    POOR = auto()
    VERY_POOR = auto()

@dataclass
class CreditFactors:
    payment_history: float  # 0-1
    credit_utilization: float  # 0-1
    length_of_credit: float  # years
    credit_mix: float  # 0-1
    new_inquiries: int

class CreditScorer:
    def __init__(self):
        self.weights = {
            "payment_history": 0.35,
            "credit_utilization": 0.30,
            "length_of_credit": 0.15,
            "credit_mix": 0.10,
            "new_inquiries": 0.10,
        }
        self.base_score = 300
        self.max_score = 850

    def calculate(self, factors: CreditFactors) -> int:
        payment = factors.payment_history * 100
        utilization = max(0, 100 - factors.credit_utilization * 100)
        length = min(factors.length_of_credit / 25 * 100, 100)
        mix = factors.credit_mix * 100
        inquiries = max(0, 100 - factors.new_inquiries * 10)
        weighted = (payment * self.weights["payment_history"] +
                    utilization * self.weights["credit_utilization"] +
                    length * self.weights["length_of_credit"] +
                    mix * self.weights["credit_mix"] +
                    inquiries * self.weights["new_inquiries"])
        score = self.base_score + (weighted / 100) * (self.max_score - self.base_score)
        return int(max(self.base_score, min(self.max_score, score)))

    def tier(self, score: int) -> CreditTier:
        if score >= 800:
            return CreditTier.EXCELLENT
        elif score >= 670:
            return CreditTier.GOOD
        elif score >= 580:
            return CreditTier.FAIR
        elif score >= 500:
            return CreditTier.POOR
        return CreditTier.VERY_POOR

    def default_probability(self, score: int) -> float:
        return max(0.001, min(0.5, math.exp(-0.02 * (score - 500))))

    def stats(self) -> Dict:
        return {"base": self.base_score, "max": self.max_score, "weights": self.weights}

def run():
    scorer = CreditScorer()
    f = CreditFactors(0.98, 0.15, 10, 0.8, 1)
    score = scorer.calculate(f)
    print("Score:", score, "Tier:", scorer.tier(score).name)
    print("Default prob:", scorer.default_probability(score))
    print(scorer.stats())

if __name__ == "__main__":
    run()
