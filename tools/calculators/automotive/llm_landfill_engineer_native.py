"""Landfill Engineer -- capacity, leachate, gas, settlement, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class LandfillEngineer:
    area_sqm: float = 100000.0
    height_m: float = 20.0
    waste_density: float = 800.0
    daily_inflow_tons: float = 500.0

    def total_capacity_tons(self) -> float:
        return self.area_sqm * self.height_m * self.waste_density / 1000

    def remaining_life_years(self) -> float:
        return self.total_capacity_tons() / (self.daily_inflow_tons * 365) if self.daily_inflow_tons > 0 else 0.0

    def leachate_estimate(self, rainfall_mm: float) -> float:
        return self.area_sqm * rainfall_mm * 0.3 / 1000

    def gas_potential(self, organic_fraction: float = 0.5) -> float:
        total_waste = self.total_capacity_tons()
        return total_waste * organic_fraction * 150

    def settlement_pct(self, years: int) -> float:
        return min(30, 5 * math.log(years + 1))

    def stats(self) -> Dict:
        return {"capacity_tons": round(self.total_capacity_tons(), 0), "remaining_years": round(self.remaining_life_years(), 1), "settlement_10y": round(self.settlement_pct(10), 1)}

def run():
    le = LandfillEngineer()
    print(le.stats())
    print("Leachate 100mm rain:", le.leachate_estimate(100))
    print("Gas potential:", le.gas_potential())

if __name__ == "__main__":
    run()
