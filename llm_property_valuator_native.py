"""Property Valuator — comparable sales, regression, cap rate, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import statistics

class PropertyValuator:
    def __init__(self):
        self.comps: List[Dict] = []
        self.subject: Dict = {}

    def add_comparable(self, props: Dict):
        self.comps.append(props)

    def set_subject(self, props: Dict):
        self.subject = props

    def comparable_value(self, adjustment_weights: Dict[str, float] = None) -> float:
        if not self.comps:
            return 0.0
        prices = []
        for comp in self.comps:
            price = comp.get("price", 0)
            prices.append(price)
        return statistics.median(prices) if prices else 0

    def income_approach(self, noi: float, cap_rate: float) -> float:
        return noi / cap_rate if cap_rate else 0

    def cost_approach(self, land_value: float, construction_cost: float, depreciation: float) -> float:
        return land_value + construction_cost - depreciation

    def regression_value(self, features: List[str]) -> float:
        if not self.comps:
            return 0.0
        # Simple average price per sqft
        prices_per_sqft = []
        for c in self.comps:
            sqft = c.get("sqft", 1)
            price = c.get("price", 0)
            if sqft > 0:
                prices_per_sqft.append(price / sqft)
        avg = statistics.mean(prices_per_sqft) if prices_per_sqft else 0
        subject_sqft = self.subject.get("sqft", 1)
        return avg * subject_sqft

    def stats(self) -> Dict:
        return {"comps": len(self.comps), "subject_set": bool(self.subject)}

def run():
    v = PropertyValuator()
    v.add_comparable({"price": 300000, "sqft": 2000, "beds": 3})
    v.add_comparable({"price": 350000, "sqft": 2200, "beds": 4})
    v.set_subject({"sqft": 2100, "beds": 3})
    print("Comp value:", v.comparable_value())
    print("Regression:", v.regression_value(["sqft"]))
    print("Income:", v.income_approach(50000, 0.05))
    print(v.stats())

if __name__ == "__main__":
    run()
