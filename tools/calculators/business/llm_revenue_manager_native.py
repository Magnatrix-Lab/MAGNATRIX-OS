"""Revenue Manager — pricing, forecasting, segmentation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class RevenueManager:
    segments: Dict[str, Dict] = field(default_factory=dict)
    """segment -> {demand, price_sensitivity, bookings}"""

    def add_segment(self, name: str, demand: int, price_sensitivity: float, bookings: int = 0):
        self.segments[name] = {"demand": demand, "sensitivity": price_sensitivity, "bookings": bookings}

    def optimal_price(self, segment: str, base_price: float, competitor_price: float) -> float:
        s = self.segments.get(segment, {})
        sensitivity = s.get("sensitivity", 1.0)
        if competitor_price < base_price:
            return base_price * (1 - 0.1 * sensitivity)
        return base_price * (1 + 0.1 * sensitivity)

    def demand_forecast(self, segment: str, trend: float = 0.0) -> int:
        s = self.segments.get(segment, {})
        base = s.get("demand", 0)
        return int(base * (1 + trend))

    def revenue_projection(self, segment: str, price: float) -> float:
        s = self.segments.get(segment, {})
        demand = s.get("demand", 0)
        return demand * price

    def total_revenue(self, prices: Dict[str, float]) -> float:
        return sum(self.revenue_projection(seg, price) for seg, price in prices.items())

    def stats(self) -> Dict:
        return {"segments": len(self.segments), "total_demand": sum(s["demand"] for s in self.segments.values())}

def run():
    rm = RevenueManager()
    rm.add_segment("Leisure", 100, 0.8)
    rm.add_segment("Business", 50, 0.3)
    print(rm.stats())
    print("Optimal leisure:", rm.optimal_price("Leisure", 150, 140))
    print("Total revenue:", rm.total_revenue({"Leisure": 140, "Business": 180}))

if __name__ == "__main__":
    run()
