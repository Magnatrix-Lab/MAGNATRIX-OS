"""Sourcing Analyzer — make vs buy, TCO, risk, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class SourcingAnalyzer:
    make_cost_per_unit: float = 0.0
    buy_cost_per_unit: float = 0.0
    make_setup_cost: float = 0.0
    buy_order_cost: float = 0.0
    volume: float = 0.0

    def tco_make(self) -> float:
        return self.make_setup_cost + self.make_cost_per_unit * self.volume

    def tco_buy(self) -> float:
        return self.buy_order_cost + self.buy_cost_per_unit * self.volume

    def break_even(self) -> float:
        diff = self.buy_cost_per_unit - self.make_cost_per_unit
        if diff == 0:
            return float('inf')
        return (self.make_setup_cost - self.buy_order_cost) / diff

    def recommend(self) -> str:
        if self.tco_make() < self.tco_buy():
            return "make"
        return "buy"

    def cost_gap(self) -> float:
        return abs(self.tco_make() - self.tco_buy())

    def stats(self) -> Dict:
        return {
            "make_tco": round(self.tco_make(), 2),
            "buy_tco": round(self.tco_buy(), 2),
            "recommend": self.recommend(),
            "break_even": round(self.break_even(), 1)
        }

def run():
    sa = SourcingAnalyzer(make_cost_per_unit=10, buy_cost_per_unit=12, make_setup_cost=5000, buy_order_cost=100, volume=2000)
    print(sa.stats())

if __name__ == "__main__":
    run()
