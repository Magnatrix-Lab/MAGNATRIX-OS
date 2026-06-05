"""Economic Modeler — supply/demand, elasticity, equilibrium, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class EconomicModeler:
    supply_curve: List[Tuple[float, float]] = field(default_factory=list)
    """price, quantity"""
    demand_curve: List[Tuple[float, float]] = field(default_factory=list)

    def equilibrium(self) -> Optional[Tuple[float, float]]:
        if not self.supply_curve or not self.demand_curve:
            return None
        for ps, qs in self.supply_curve:
            for pd, qd in self.demand_curve:
                if abs(qs - qd) < 0.01 and abs(ps - pd) < 0.01:
                    return ps, qs
        return None

    def price_elasticity(self, p1: float, q1: float, p2: float, q2: float) -> float:
        if p1 == p2 or q1 == 0:
            return 0.0
        return ((q2 - q1) / q1) / ((p2 - p1) / p1)

    def consumer_surplus(self, max_price: float, equilibrium_price: float, equilibrium_qty: float) -> float:
        return (max_price - equilibrium_price) * equilibrium_qty / 2

    def producer_surplus(self, min_price: float, equilibrium_price: float, equilibrium_qty: float) -> float:
        return (equilibrium_price - min_price) * equilibrium_qty / 2

    def stats(self) -> Dict:
        return {"supply_points": len(self.supply_curve), "demand_points": len(self.demand_curve)}

def run():
    em = EconomicModeler(supply_curve=[(1,10),(2,20),(3,30)], demand_curve=[(3,10),(2,20),(1,30)])
    print("Equilibrium:", em.equilibrium())
    print("Elasticity:", em.price_elasticity(2, 20, 3, 10))
    print(em.stats())

if __name__ == "__main__":
    run()
