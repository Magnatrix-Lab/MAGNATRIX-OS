"""Customer Lifetime Value — churn, acquisition, retention, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class CustomerLifetime:
    avg_order_value: float = 100.0
    purchase_frequency: float = 2.0
    lifespan_years: float = 3.0
    gross_margin: float = 0.3
    acquisition_cost: float = 50.0

    def clv(self) -> float:
        return self.avg_order_value * self.purchase_frequency * self.lifespan_years * self.gross_margin

    def clv_net(self) -> float:
        return self.clv() - self.acquisition_cost

    def payback_period(self) -> float:
        annual_profit = self.avg_order_value * self.purchase_frequency * self.gross_margin
        return self.acquisition_cost / annual_profit if annual_profit > 0 else float('inf')

    def churn_rate(self, customers_start: int, customers_end: int) -> float:
        if customers_start == 0:
            return 0.0
        return (customers_start - customers_end) / customers_start

    def retention_rate(self, churn: float) -> float:
        return 1 - churn

    def cohort_value(self, cohort_size: int, months: int) -> float:
        retention = self.retention_rate(self.churn_rate(100, 80))
        return cohort_size * self.avg_order_value * self.gross_margin * retention ** months

    def stats(self) -> Dict:
        return {"clv": round(self.clv(), 2), "net_clv": round(self.clv_net(), 2), "payback": round(self.payback_period(), 2)}

def run():
    cl = CustomerLifetime(avg_order_value=200, purchase_frequency=4, lifespan_years=5, gross_margin=0.4, acquisition_cost=100)
    print(cl.stats())
    print("Churn:", cl.churn_rate(1000, 800))
    print("Cohort value:", cl.cohort_value(100, 12))

if __name__ == "__main__":
    run()
