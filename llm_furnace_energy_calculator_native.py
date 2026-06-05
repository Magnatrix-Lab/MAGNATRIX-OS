"""Native stdlib module: Furnace Energy Calculator
Calculates furnace energy consumption, propane usage, and costs.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FurnaceEnergyCalculator:
    chamber_volume_l: float
    max_temp_c: float
    operating_hours_per_day: float = 8.0
    insulation_factor: float = 1.0  # 1.0 = good, 1.5 = poor
    propane_cost_per_gal: float = 3.5

    def max_power_kw(self) -> float:
        return self.chamber_volume_l * 0.08 * self.insulation_factor

    def daily_energy_kwh(self) -> float:
        return self.max_power_kw() * self.operating_hours_per_day * 0.6

    def monthly_energy_kwh(self, days_per_month: float = 22.0) -> float:
        return self.daily_energy_kwh() * days_per_month

    def propane_gallons_per_day(self) -> float:
        kwh_per_gallon = 26.8
        return self.daily_energy_kwh() / kwh_per_gallon

    def daily_cost_usd(self) -> float:
        return self.propane_gallons_per_day() * self.propane_cost_per_gal

    def monthly_cost_usd(self, days_per_month: float = 22.0) -> float:
        return self.daily_cost_usd() * days_per_month

    def stats(self, days_per_month: float = 22.0) -> Dict:
        return {
            "max_power_kw": round(self.max_power_kw(), 1),
            "daily_energy_kwh": round(self.daily_energy_kwh(), 1),
            "monthly_energy_kwh": round(self.monthly_energy_kwh(days_per_month), 1),
            "propane_gallons_per_day": round(self.propane_gallons_per_day(), 2),
            "daily_cost_usd": round(self.daily_cost_usd(), 2),
            "monthly_cost_usd": round(self.monthly_cost_usd(days_per_month), 2),
        }

def run():
    fec = FurnaceEnergyCalculator(chamber_volume_l=200, max_temp_c=1100, operating_hours_per_day=6)
    print(fec.stats())

if __name__ == "__main__":
    run()
