"""Dispute Resolver — negotiation, arbitration, scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class DisputeResolver:
    def __init__(self):
        self.disputes: List[Dict] = []
        self.resolutions: List[Dict] = []

    def add_dispute(self, dispute_id: str, party_a: str, party_b: str, claim_amount: float, evidence_strength: float = 0.5):
        self.disputes.append({"id": dispute_id, "a": party_a, "b": party_b, "claim": claim_amount, "evidence": evidence_strength})

    def negotiate(self, dispute_id: str, a_offer: float, b_offer: float) -> Dict:
        dispute = next((d for d in self.disputes if d["id"] == dispute_id), None)
        if not dispute:
            return {}
        gap = abs(a_offer - b_offer)
        midpoint = (a_offer + b_offer) / 2
        if gap / dispute["claim"] < 0.1:
            result = {"status": "SETTLED", "amount": midpoint, "gap": gap}
        elif gap / dispute["claim"] < 0.3:
            result = {"status": "LIKELY_SETTLE", "amount": midpoint, "gap": gap}
        else:
            result = {"status": "ARBITRATION_NEEDED", "gap": gap}
        self.resolutions.append(result)
        return result

    def arbitrate(self, dispute_id: str, evidence_a: float, evidence_b: float) -> Dict:
        dispute = next((d for d in self.disputes if d["id"] == dispute_id), None)
        if not dispute:
            return {}
        if evidence_a > evidence_b + 0.2:
            result = {"winner": "A", "award": dispute["claim"] * 0.8}
        elif evidence_b > evidence_a + 0.2:
            result = {"winner": "B", "award": 0}
        else:
            result = {"winner": "SPLIT", "award": dispute["claim"] * 0.5}
        self.resolutions.append(result)
        return result

    def stats(self) -> Dict:
        return {"disputes": len(self.disputes), "resolutions": len(self.resolutions)}

def run():
    dr = DisputeResolver()
    dr.add_dispute("D1", "A", "B", 10000, 0.7)
    print(dr.negotiate("D1", 8000, 7500))
    print(dr.arbitrate("D1", 0.8, 0.3))
    print(dr.stats())

if __name__ == "__main__":
    run()
