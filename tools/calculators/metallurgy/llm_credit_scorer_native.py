"""Credit Scorer — FICO-like, payment history, utilization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class CreditScorer:
    payment_history: float = 0.95
    credit_utilization: float = 0.3
    length_of_credit: float = 5.0
    new_credit: int = 1
    credit_mix: float = 0.5

    def payment_history_score(self) -> float:
        return 300 + self.payment_history * 192

    def utilization_score(self) -> float:
        return max(0, 120 - self.credit_utilization * 400)

    def length_score(self) -> float:
        return min(75, self.length_of_credit * 15)

    def new_credit_score(self) -> float:
        return max(0, 55 - self.new_credit * 10)

    def credit_mix_score(self) -> float:
        return self.credit_mix * 50

    def total_score(self) -> float:
        return sum([self.payment_history_score(), self.utilization_score(), self.length_score(), self.new_credit_score(), self.credit_mix_score()])

    def rating(self) -> str:
        s = self.total_score()
        if s >= 800: return "exceptional"
        elif s >= 740: return "very good"
        elif s >= 670: return "good"
        elif s >= 580: return "fair"
        return "poor"

    def stats(self) -> Dict:
        return {"score": round(self.total_score(), 0), "rating": self.rating()}

def run():
    cs = CreditScorer(payment_history=0.98, credit_utilization=0.15, length_of_credit=10, credit_mix=0.8)
    print(cs.stats())

if __name__ == "__main__":
    run()
