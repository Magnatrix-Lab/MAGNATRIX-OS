"""Claims Processor — fraud detection, reserving, payout, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

@dataclass
class Claim:
    id: str
    policy_id: str
    amount: float
    date: str
    status: str = "pending"
    fraud_flags: int = 0

class ClaimsProcessor:
    def __init__(self):
        self.claims: List[Claim] = []

    def add_claim(self, c: Claim):
        self.claims.append(c)

    def total_pending(self) -> float:
        return sum(c.amount for c in self.claims if c.status == "pending")

    def total_paid(self) -> float:
        return sum(c.amount for c in self.claims if c.status == "paid")

    def fraud_score(self, claim: Claim) -> float:
        score = 0.0
        if claim.amount > 50000:
            score += 0.3
        if claim.fraud_flags > 2:
            score += 0.4
        if claim.status == "pending" and (datetime.now() - datetime.strptime(claim.date, "%Y-%m-%d")).days > 30:
            score += 0.2
        return min(1.0, score)

    def suspicious_claims(self) -> List[Claim]:
        return [c for c in self.claims if self.fraud_score(c) > 0.5]

    def reserve_requirement(self) -> float:
        return self.total_pending() * 1.2

    def stats(self) -> Dict:
        return {"claims": len(self.claims), "pending": round(self.total_pending(), 2), "paid": round(self.total_paid(), 2), "suspicious": len(self.suspicious_claims())}

def run():
    cp = ClaimsProcessor()
    cp.add_claim(Claim("C1", "P1", 10000, "2024-01-01"))
    cp.add_claim(Claim("C2", "P1", 75000, "2024-02-01", fraud_flags=3))
    cp.add_claim(Claim("C3", "P2", 5000, "2024-03-01", status="paid"))
    print(cp.stats())
    print("Reserve:", cp.reserve_requirement())

if __name__ == "__main__":
    run()
