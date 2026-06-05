"""Fuel Consumption Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FuelConsumption:
    distance_km: float
    fuel_used_liters: float
    fuel_type: str = "gasoline"

    def liters_per_100km(self) -> float:
        if self.distance_km <= 0:
            return 0.0
        return round(self.fuel_used_liters / self.distance_km * 100, 2)

    def km_per_liter(self) -> float:
        if self.fuel_used_liters <= 0:
            return 0.0
        return round(self.distance_km / self.fuel_used_liters, 2)

    def mpg_us(self) -> float:
        if self.fuel_used_liters <= 0:
            return 0.0
        km_per_l = self.km_per_liter()
        return round(km_per_l * 2.352, 2)

    def mpg_uk(self) -> float:
        if self.fuel_used_liters <= 0:
            return 0.0
        km_per_l = self.km_per_liter()
        return round(km_per_l * 2.825, 2)

    def co2_emissions_g_per_km(self) -> float:
        factors = {"gasoline": 2300, "diesel": 2640, "lpg": 1600, "cng": 1800, "ethanol": 1500}
        factor = factors.get(self.fuel_type, 2300)
        l_100km = self.liters_per_100km()
        return round(factor * l_100km / 100.0, 2)

    def fuel_cost(self, price_per_liter: float) -> float:
        return round(self.fuel_used_liters * price_per_liter, 2)

    def cost_per_km(self, price_per_liter: float) -> float:
        if self.distance_km <= 0:
            return 0.0
        return round(self.fuel_cost(price_per_liter) / self.distance_km, 3)

    def stats(self) -> Dict[str, float]:
        return {
            "liters_per_100km": self.liters_per_100km(),
            "km_per_liter": self.km_per_liter(),
            "mpg_us": self.mpg_us(),
        }

    def run(self):
        print("=" * 60)
        print("FUEL CONSUMPTION CALCULATOR")
        print("=" * 60)
        fc = FuelConsumption(
            distance_km=500, fuel_used_liters=35, fuel_type="diesel"
        )
        print(f"Distance: {fc.distance_km} km")
        print(f"Fuel used: {fc.fuel_used_liters} L")
        print(f"L/100km: {fc.liters_per_100km():.2f}")
        print(f"km/L: {fc.km_per_liter():.2f}")
        print(f"MPG (US): {fc.mpg_us():.2f}")
        print(f"MPG (UK): {fc.mpg_uk():.2f}")
        print(f"CO2: {fc.co2_emissions_g_per_km():.2f} g/km")
        print(f"Cost @ $1.5/L: ${fc.fuel_cost(1.5):.2f}")
        print(f"Stats: {fc.stats()}")

if __name__ == "__main__":
    FuelConsumption(0, 0).run()
