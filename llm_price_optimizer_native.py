"""Price Optimizer — elasticity, profit, markdown, bundling, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class PriceOptimizer:
    cost: float = 10.0
    current_price: float = 20.0
    current_demand: float = 100.0
    elasticity: float = -1.5

    def optimal_price(self) -> float:
        if self.elasticity == 0 or self.elasticity == -1:
            return self.current_price
        return self.cost * self.elasticity / (1 + self.elasticity)

    def profit(self, price: float) -> float:
        if self.elasticity == 0:
            return 0.0
        q = self.current_demand * (price / self.current_price) ** self.elasticity
        return (price - self.cost) * q

    def markdown_price(self, target_clearance: float, weeks_left: int) -> float:
        if weeks_left <= 0:
            return self.cost
        return self.current_price * (1 - target_clearance) ** (1 / weeks_left)

    def bundle_price(self, items: List[float], discount: float = 0.1) -> float:
        total = sum(items)
        return total * (1 - discount)

    def stats(self) -> Dict:
        return {"optimal": round(self.optimal_price(), 2), "current_profit": round(self.profit(self.current_price), 2), "optimal_profit": round(self.profit(self.optimal_price()), 2)}

def run():
    po = PriceOptimizer(cost=15, current_price=30, current_demand=200, elasticity=-2.0)
    print(po.stats())
    print("Markdown:", po.markdown_price(0.8, 4))
    print("Bundle:", po.bundle_price([20, 25, 15]))

if __name__ == "__main__":
    run()
