"""Dispute Resolver — negotiation, mediation, arbitration scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class DisputeResolver:
    party_a: str = ""
    party_b: str = ""
    claims: List[Dict] = field(default_factory=list)

    def add_claim(self, party: str, amount: float, merit: float):
        self.claims.append({"party": party, "amount": amount, "merit": merit})

    def total_claimed(self, party: str) -> float:
        return sum(c["amount"] for c in self.claims if c["party"] == party)

    def weighted_merit(self, party: str) -> float:
        claims = [c for c in self.claims if c["party"] == party]
        if not claims:
            return 0.0
        return sum(c["amount"] * c["merit"] for c in claims) / sum(c["amount"] for c in claims)

    def proposed_settlement(self) -> float:
        a_merit = self.weighted_merit(self.party_a)
        b_merit = self.weighted_merit(self.party_b)
        a_claim = self.total_claimed(self.party_a)
        b_claim = self.total_claimed(self.party_b)
        if a_merit > b_merit:
            return a_claim * 0.7 - b_claim * 0.3
        return b_claim * 0.7 - a_claim * 0.3

    def mediation_score(self) -> float:
        a_merit = self.weighted_merit(self.party_a)
        b_merit = self.weighted_merit(self.party_b)
        return 1 - abs(a_merit - b_merit)

    def stats(self) -> Dict:
        return {"claims": len(self.claims), "settlement": round(self.proposed_settlement(), 2), "mediation_score": round(self.mediation_score(), 3)}

def run():
    dr = DisputeResolver("Buyer", "Seller")
    dr.add_claim("Buyer", 10000, 0.8)
    dr.add_claim("Seller", 5000, 0.6)
    print(dr.stats())

if __name__ == "__main__":
    run()
