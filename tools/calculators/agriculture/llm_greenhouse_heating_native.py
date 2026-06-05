"""Greenhouse Heating Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class GreenhouseHeating:
    greenhouse_area_sqm: float
    target_temp_c: float
    outside_temp_c: float
    u_value_w_per_m2_k: float = 6.0
    insulation_factor: float = 1.0

    def heat_loss_w(self) -> float:
        delta_t = self.target_temp_c - self.outside_temp_c
        return round(self.greenhouse_area_sqm * self.u_value_w_per_m2_k * delta_t / self.insulation_factor, 1)

    def heat_loss_kw(self) -> float:
        return round(self.heat_loss_w() / 1000, 2)

    def daily_energy_kwh(self) -> float:
        return round(self.heat_loss_kw() * 24, 2)

    def fuel_required_liters(self, fuel_energy_mj_per_liter: float = 36.0,
                               boiler_efficiency: float = 80.0) -> float:
        if fuel_energy_mj_per_liter <= 0 or boiler_efficiency <= 0:
            return 0.0
        energy_mj = self.daily_energy_kwh() * 3.6
        return round(energy_mj / (fuel_energy_mj_per_liter * boiler_efficiency / 100.0), 2)

    def cost_per_day(self, fuel_price_per_liter: float = 1.0) -> float:
        return round(self.fuel_required_liters() * fuel_price_per_liter, 2)

    def co2_generation_kg(self) -> float:
        liters = self.fuel_required_liters()
        return round(liters * 2.7, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "heat_loss_kw": self.heat_loss_kw(),
            "daily_energy_kwh": self.daily_energy_kwh(),
            "fuel_required_liters": self.fuel_required_liters(),
        }

    def run(self):
        print("=" * 60)
        print("GREENHOUSE HEATING CALCULATOR")
        print("=" * 60)
        gh = GreenhouseHeating(
            greenhouse_area_sqm=500, target_temp_c=20, outside_temp_c=-5,
            u_value_w_per_m2_k=6.5, insulation_factor=1.1
        )
        print(f"Area: {gh.greenhouse_area_sqm} sqm")
        print(f"Target: {gh.target_temp_c} C, Outside: {gh.outside_temp_c} C")
        print(f"Heat loss: {gh.heat_loss_w():.1f} W ({gh.heat_loss_kw():.2f} kW)")
        print(f"Daily energy: {gh.daily_energy_kwh():.2f} kWh")
        print(f"Fuel: {gh.fuel_required_liters():.2f} L/day")
        print(f"Cost: ${gh.cost_per_day():.2f}/day")
        print(f"CO2: {gh.co2_generation_kg():.2f} kg/day")
        print(f"Stats: {gh.stats()}")

if __name__ == "__main__":
    GreenhouseHeating(0, 0, 0).run()
