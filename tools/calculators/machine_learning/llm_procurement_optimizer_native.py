"""Procurement Optimizer — bidding, scoring, award, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Bid:
    vendor: str
    price: float
    quality: float
    delivery: float
    reliability: float

class ProcurementOptimizer:
    def __init__(self):
        self.bids: List[Bid] = []
        self.weights = {"price": 0.4, "quality": 0.3, "delivery": 0.2, "reliability": 0.1}

    def add_bid(self, b: Bid):
        self.bids.append(b)

    def score(self, b: Bid) -> float:
        min_price = min(x.price for x in self.bids) if self.bids else 1
        price_score = min_price / b.price if b.price > 0 else 0
        return (
            price_score * self.weights["price"] +
            b.quality * self.weights["quality"] +
            b.delivery * self.weights["delivery"] +
            b.reliability * self.weights["reliability"]
        )

    def best_bid(self) -> Optional[Bid]:
        if not self.bids:
            return None
        return max(self.bids, key=lambda b: self.score(b))

    def cost_quality_ratio(self, b: Bid) -> float:
        return b.quality / b.price if b.price > 0 else 0

    def award(self) -> Dict:
        best = self.best_bid()
        return {"vendor": best.vendor if best else None, "score": round(self.score(best), 3) if best else 0}

    def stats(self) -> Dict:
        return {"bids": len(self.bids), "best": self.award(), "avg_price": sum(b.price for b in self.bids) / len(self.bids) if self.bids else 0}

def run():
    po = ProcurementOptimizer()
    po.add_bid(Bid("A", 1000, 0.9, 0.8, 0.95))
    po.add_bid(Bid("B", 800, 0.7, 0.9, 0.8))
    po.add_bid(Bid("C", 1200, 0.95, 0.7, 0.9))
    print(po.stats())
    print("All scores:", [(b.vendor, round(po.score(b), 3)) for b in po.bids])

if __name__ == "__main__":
    run()
