"""Native stdlib module: Wind Turbine Calculator
Estimates wind turbine power output by swept area, wind speed, and air density.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class WindTurbineCalculator:
    rotor_diameter_m: float
    wind_speed_ms: float
    air_density_kg_m3: float = 1.225
    efficiency_pct: float = 35.0
    cut_in_speed_ms: float = 3.0
    cut_out_speed_ms: float = 25.0

    def swept_area(self) -> float:
        return math.pi * (self.rotor_diameter_m / 2) ** 2

    def theoretical_power(self) -> float:
        return 0.5 * self.air_density_kg_m3 * self.swept_area() * (self.wind_speed_ms ** 3)

    def actual_power(self) -> float:
        if self.wind_speed_ms < self.cut_in_speed_ms or self.wind_speed_ms > self.cut_out_speed_ms:
            return 0.0
        return self.theoretical_power() * (self.efficiency_pct / 100)

    def annual_energy_mwh(self, capacity_factor: float = 0.35) -> float:
        return self.actual_power() * 8760 * capacity_factor / 1000

    def stats(self) -> Dict[str, float]:
        return {
            "swept_area_m2": round(self.swept_area(), 1),
            "theoretical_power_kw": round(self.theoretical_power() / 1000, 1),
            "actual_power_kw": round(self.actual_power() / 1000, 1),
            "annual_energy_mwh": round(self.annual_energy_mwh(), 1),
        }

def run():
    wt = WindTurbineCalculator(rotor_diameter_m=80, wind_speed_ms=8, efficiency_pct=35)
    print(wt.stats())

if __name__ == "__main__":
    run()
