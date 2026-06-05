"""Fuel Efficiency Calculator — MPG, L/100km, emissions, cost, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class FuelEfficiencyCalculator:
    distance_km: float = 100.0
    fuel_liters: float = 8.0
    fuel_price_per_liter: float = 1.5
    co2_per_liter: float = 2.31

    def l_per_100km(self) -> float:
        return (self.fuel_liters / self.distance_km) * 100 if self.distance_km > 0 else 0.0

    def mpg(self) -> float:
        liters_per_100km = self.l_per_100km()
        return 235.215 / liters_per_100km if liters_per_100km > 0 else 0.0

    def cost_per_km(self) -> float:
        return (self.fuel_liters * self.fuel_price_per_liter) / self.distance_km if self.distance_km > 0 else 0.0

    def co2_emissions(self) -> float:
        return self.fuel_liters * self.co2_per_liter

    def annual_cost(self, annual_km: float = 15000) -> float:
        return self.cost_per_km() * annual_km

    def compare(self, other_l_per_100km: float) -> float:
        return self.l_per_100km() - other_l_per_100km

    def stats(self) -> Dict:
        return {
            "l_per_100km": round(self.l_per_100km(), 2),
            "mpg": round(self.mpg(), 1),
            "cost_per_km": round(self.cost_per_km(), 3),
            "co2_kg": round(self.co2_emissions(), 2)
        }

def run():
    fec = FuelEfficiencyCalculator(distance_km=500, fuel_liters=35, fuel_price_per_liter=1.8)
    print(fec.stats())
    print("Annual cost:", fec.annual_cost())

if __name__ == "__main__":
    run()
