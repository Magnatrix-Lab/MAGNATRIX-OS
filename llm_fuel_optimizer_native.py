"""Fuel Optimizer — tankering, step climb, alternate planning, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class FuelOptimizer:
    fuel_price_base: float = 1.0
    fuel_price_dest: float = 1.5
    tank_capacity: float = 20000.0
    burn_rate: float = 3000.0

    def tankering_benefit(self, trip_fuel: float) -> float:
        extra = min(self.tank_capacity - trip_fuel, trip_fuel * 0.3)
        burn_penalty = extra * 0.04
        savings = extra * (self.fuel_price_dest - self.fuel_price_base)
        return savings - burn_penalty * self.fuel_price_base

    def step_climb_benefit(self, alt1: float, alt2: float, distance: float) -> float:
        fuel_alt1 = distance * self.burn_rate * 1.0
        fuel_alt2 = distance * self.burn_rate * 0.85
        return fuel_alt1 - fuel_alt2

    def alternate_fuel(self, distance_to_alt: float) -> float:
        return distance_to_alt * self.burn_rate * 1.1 + 1000.0

    def contingency_fuel(self, trip_fuel: float) -> float:
        return trip_fuel * 0.05

    def final_reserve(self) -> float:
        return 30.0 * self.burn_rate / 60.0

    def stats(self, trip_fuel: float) -> Dict:
        return {"tankering": round(self.tankering_benefit(trip_fuel), 0), "contingency": round(self.contingency_fuel(trip_fuel), 0), "reserve": round(self.final_reserve(), 0)}

def run():
    fo = FuelOptimizer()
    print(fo.stats(10000))
    print("Alternate fuel:", fo.alternate_fuel(200))
    print("Step climb benefit:", fo.step_climb_benefit(30000, 35000, 1000))

if __name__ == "__main__":
    run()
