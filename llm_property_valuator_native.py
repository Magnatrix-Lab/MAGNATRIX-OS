"""Property Valuator — comps, cap rate, DCF, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class PropertyValuator:
    price: float = 0.0
    income: float = 0.0
    expenses: float = 0.0
    area: float = 0.0

    def cap_rate(self) -> float:
        noi = self.income - self.expenses
        return noi / self.price if self.price > 0 else 0.0

    def price_per_sqft(self) -> float:
        return self.price / self.area if self.area > 0 else 0.0

    def dcf_value(self, cash_flows: List[float], discount_rate: float = 0.08) -> float:
        return sum(cf / ((1 + discount_rate) ** (i + 1)) for i, cf in enumerate(cash_flows))

    def comparable_value(self, comps: List[float], weights: List[float]) -> float:
        if not comps or not weights or len(comps) != len(weights):
            return 0.0
        return sum(c * w for c, w in zip(comps, weights)) / sum(weights)

    def gross_rent_multiplier(self) -> float:
        return self.price / self.income if self.income > 0 else 0.0

    def stats(self) -> Dict:
        return {"cap_rate": round(self.cap_rate(), 4), "price_per_sqft": round(self.price_per_sqft(), 2)}

def run():
    pv = PropertyValuator(price=500000, income=40000, expenses=15000, area=2000)
    print(pv.stats())
    print("DCF:", pv.dcf_value([25000, 26000, 27000]))
    print("GRM:", pv.gross_rent_multiplier())

if __name__ == "__main__":
    run()
