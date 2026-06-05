"""Claim Estimator — severity, reserve, IBNR, payout, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Claim:
    id: str
    reported_amount: float
    severity: str
    status: str

class ClaimEstimator:
    def __init__(self):
        self.claims: List[Claim] = []

    def add_claim(self, c: Claim):
        self.claims.append(c)

    def severity_factor(self, severity: str) -> float:
        return {"minor": 0.5, "moderate": 1.0, "major": 2.5, "catastrophic": 5.0}.get(severity, 1.0)

    def case_reserve(self, claim: Claim) -> float:
        return claim.reported_amount * self.severity_factor(claim.severity)

    def total_reserve(self) -> float:
        return sum(self.case_reserve(c) for c in self.claims if c.status == "open")

    def ibnr(self, expected_count: int, avg_severity: float) -> float:
        reported_count = len(self.claims)
        return max(0, (expected_count - reported_count)) * avg_severity

    def loss_ratio(self, earned_premium: float) -> float:
        if earned_premium == 0:
            return 0.0
        total_paid = sum(c.reported_amount for c in self.claims)
        return total_paid / earned_premium

    def stats(self) -> Dict:
        return {"claims": len(self.claims), "open_reserve": round(self.total_reserve(), 2), "avg_reported": sum(c.reported_amount for c in self.claims) / len(self.claims) if self.claims else 0}

def run():
    ce = ClaimEstimator()
    ce.add_claim(Claim("C1", 5000, "moderate", "open"))
    ce.add_claim(Claim("C2", 25000, "major", "open"))
    ce.add_claim(Claim("C3", 1000, "minor", "closed"))
    print(ce.stats())
    print("IBNR:", ce.ibnr(10, 8000))
    print("Loss ratio:", ce.loss_ratio(100000))

if __name__ == "__main__":
    run()
