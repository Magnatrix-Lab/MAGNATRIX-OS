"""Native stdlib module: Shipping Calculator
Estimates shipping costs by weight, dimensions, distance, and service level.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ServiceLevel(Enum):
    GROUND = "ground"
    EXPRESS = "express"
    OVERNIGHT = "overnight"
    INTERNATIONAL = "international"

@dataclass
class ShippingCalculator:
    weight_kg: float
    length_cm: float
    width_cm: float
    height_cm: float
    distance_km: float
    service_level: ServiceLevel
    base_rate_per_kg: float = 1.5
    fuel_surcharge_pct: float = 8.0

    def dimensional_weight(self) -> float:
        dim_weight = (self.length_cm * self.width_cm * self.height_cm) / 5000
        return max(dim_weight, self.weight_kg)

    def service_multiplier(self) -> float:
        multipliers = {
            ServiceLevel.GROUND: 1.0,
            ServiceLevel.EXPRESS: 2.5,
            ServiceLevel.OVERNIGHT: 5.0,
            ServiceLevel.INTERNATIONAL: 3.5,
        }
        return multipliers.get(self.service_level, 1.0)

    def base_cost(self) -> float:
        return self.dimensional_weight() * self.distance_km * self.base_rate_per_kg * self.service_multiplier() / 100

    def total_cost(self) -> float:
        return self.base_cost() * (1 + self.fuel_surcharge_pct / 100)

    def stats(self) -> Dict[str, float]:
        return {
            "billable_weight_kg": round(self.dimensional_weight(), 2),
            "base_cost": round(self.base_cost(), 2),
            "total_cost": round(self.total_cost(), 2),
            "service": self.service_level.value,
        }

def run():
    sc = ShippingCalculator(weight_kg=5, length_cm=40, width_cm=30, height_cm=20, distance_km=800, service_level=ServiceLevel.EXPRESS)
    print(sc.stats())

if __name__ == "__main__":
    run()
