"""Carbon Footprint Calculator — emissions, offsets, scope 1/2/3, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class CarbonFootprint:
    scope1: float = 0.0
    scope2: float = 0.0
    scope3: float = 0.0
    offsets: float = 0.0

    def total(self) -> float:
        return self.scope1 + self.scope2 + self.scope3

    def net(self) -> float:
        return max(0, self.total() - self.offsets)

    def intensity(self, revenue: float) -> float:
        return self.net() / revenue if revenue > 0 else 0.0

    def breakdown(self) -> Dict[str, float]:
        total = self.total()
        if total == 0:
            return {"scope1": 0, "scope2": 0, "scope3": 0}
        return {"scope1": self.scope1/total, "scope2": self.scope2/total, "scope3": self.scope3/total}

    def target_reduction(self, year: int, base_year: int, base_emissions: float, target_pct: float) -> float:
        years = year - base_year
        annual_rate = (1 - target_pct/100) ** (1 / max(years, 1))
        return base_emissions * (annual_rate ** years)

    def stats(self) -> Dict:
        return {"total": self.total(), "net": self.net(), "breakdown": self.breakdown()}

def run():
    cf = CarbonFootprint(scope1=100, scope2=200, scope3=500, offsets=50)
    print(cf.stats())
    print("Target 2030:", cf.target_reduction(2030, 2024, 800, 30))

if __name__ == "__main__":
    run()
