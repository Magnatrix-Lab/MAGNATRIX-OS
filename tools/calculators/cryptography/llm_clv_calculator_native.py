"""CLV Calculator — customer lifetime value, cohort analysis, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class CLVCalculator:
    def __init__(self, discount_rate: float = 0.1):
        self.discount_rate = discount_rate
        self.customers: Dict[str, Dict] = {}

    def add_customer(self, customer_id: str, avg_order_value: float, purchase_freq: float, lifespan: float, margin: float = 0.3):
        self.customers[customer_id] = {
            "aov": avg_order_value,
            "freq": purchase_freq,
            "lifespan": lifespan,
            "margin": margin,
        }

    def calculate(self, customer_id: str) -> float:
        c = self.customers.get(customer_id, {})
        if not c:
            return 0.0
        clv = c["aov"] * c["freq"] * c["lifespan"] * c["margin"]
        return clv

    def calculate_with_discount(self, customer_id: str) -> float:
        c = self.customers.get(customer_id, {})
        if not c:
            return 0.0
        clv = 0.0
        for t in range(int(c["lifespan"])):
            clv += (c["aov"] * c["freq"] * c["margin"]) / ((1 + self.discount_rate) ** t)
        return clv

    def cohort_clv(self, cohort_customers: List[str]) -> float:
        return sum(self.calculate(c) for c in cohort_customers) / len(cohort_customers) if cohort_customers else 0

    def stats(self) -> Dict:
        return {"customers": len(self.customers), "avg_clv": sum(self.calculate(c) for c in self.customers) / len(self.customers) if self.customers else 0}

def run():
    clv = CLVCalculator(0.1)
    clv.add_customer("C1", 100, 12, 5, 0.3)
    clv.add_customer("C2", 50, 6, 3, 0.25)
    print("CLV C1:", clv.calculate("C1"))
    print("Discounted CLV C1:", clv.calculate_with_discount("C1"))
    print(clv.stats())

if __name__ == "__main__":
    run()
