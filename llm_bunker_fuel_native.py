"""Native stdlib module: Bunker Fuel Calculator
Calculates bunker fuel consumption, voyage costs, and emissions for shipping.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class FuelType(Enum):
    HFO = "hfo"
    MDO = "mdo"
    MGO = "mgo"
    LNG = "lng"

@dataclass
class BunkerFuelCalculator:
    voyage_distance_nm: float
    vessel_speed_kts: float
    fuel_consumption_ton_per_day: float
    fuel_type: FuelType
    fuel_price_usd_per_ton: float

    def voyage_days(self) -> float:
        if self.vessel_speed_kts == 0:
            return 0.0
        return self.voyage_distance_nm / (self.vessel_speed_kts * 24)

    def total_fuel_ton(self) -> float:
        return self.voyage_days() * self.fuel_consumption_ton_per_day

    def fuel_cost_usd(self) -> float:
        return self.total_fuel_ton() * self.fuel_price_usd_per_ton

    def co2_emissions_ton(self) -> float:
        factors = {FuelType.HFO: 3.41, FuelType.MDO: 3.19, FuelType.MGO: 3.19, FuelType.LNG: 2.75}
        return self.total_fuel_ton() * factors.get(self.fuel_type, 3.2)

    def sox_emissions_kg(self) -> float:
        sulfur_content = {FuelType.HFO: 0.035, FuelType.MDO: 0.001, FuelType.MGO: 0.001, FuelType.LNG: 0.0}
        return self.total_fuel_ton() * sulfur_content.get(self.fuel_type, 0.01) * 20

    def optimal_speed_kts(self, reference_speed: float = 20, reference_consumption: float = 50) -> float:
        return (4 * reference_speed**3 / reference_consumption) ** 0.25

    def stats(self) -> Dict:
        return {
            "voyage_distance_nm": self.voyage_distance_nm,
            "voyage_days": round(self.voyage_days(), 1),
            "total_fuel_ton": round(self.total_fuel_ton(), 1),
            "fuel_cost_usd": round(self.fuel_cost_usd(), 2),
            "co2_emissions_ton": round(self.co2_emissions_ton(), 1),
            "sox_emissions_kg": round(self.sox_emissions_kg(), 1),
        }

def run():
    bfc = BunkerFuelCalculator(voyage_distance_nm=5000, vessel_speed_kts=18, fuel_consumption_ton_per_day=40, fuel_type=FuelType.HFO, fuel_price_usd_per_ton=450)
    print(bfc.stats())

if __name__ == "__main__":
    run()
