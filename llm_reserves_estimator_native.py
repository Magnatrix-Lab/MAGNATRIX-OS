"""Reserves Estimator — inferred, indicated, measured, JORC, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ReservesEstimator:
    measured_tons: float = 0.0
    indicated_tons: float = 0.0
    inferred_tons: float = 0.0
    grade: float = 0.0
    recovery: float = 0.85

    def total_resources(self) -> float:
        return self.measured_tons + self.indicated_tons + self.inferred_tons

    def total_reserves(self, measured_conf: float = 1.0, indicated_conf: float = 0.7, inferred_conf: float = 0.3) -> float:
        return self.measured_tons * measured_conf + self.indicated_tons * indicated_conf + self.inferred_tons * inferred_conf

    def contained_metal(self) -> float:
        return self.total_resources() * self.grade

    def recoverable_metal(self) -> float:
        return self.contained_metal() * self.recovery

    def mine_life(self, annual_production: float) -> float:
        return self.total_reserves() / annual_production if annual_production > 0 else 0.0

    def value(self, metal_price: float) -> float:
        return self.recoverable_metal() * metal_price

    def stats(self) -> Dict:
        return {"total_resources": self.total_resources(), "reserves": round(self.total_reserves(), 0), "mine_life": round(self.mine_life(10000), 1)}

def run():
    re = ReservesEstimator(measured_tons=100000, indicated_tons=200000, inferred_tons=500000, grade=0.02, recovery=0.9)
    print(re.stats())
    print("Value at $50k/ton:", re.value(50000))

if __name__ == "__main__":
    run()
