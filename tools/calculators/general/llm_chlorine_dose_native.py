"""Chlorine Dose Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ChlorineDose:
    water_flow_m3_h: float
    chlorine_demand_mg_l: float
    target_residual_mg_l: float = 0.5
    chlorine_type: str = "gas"

    def total_dose_mg_l(self) -> float:
        return round(self.chlorine_demand_mg_l + self.target_residual_mg_l, 2)

    def daily_dose_kg(self) -> float:
        return round(self.total_dose_mg_l() * self.water_flow_m3_h * 24 / 1000.0, 2)

    def chlorine_concentration_percent(self) -> float:
        concentrations = {"gas": 100, "hypochlorite_12": 12, "hypochlorite_5": 5, "bleach": 5, "chloramine": 25}
        return concentrations.get(self.chlorine_type, 12)

    def solution_volume_liters_per_day(self) -> float:
        conc = self.chlorine_concentration_percent()
        if conc <= 0:
            return 0.0
        daily = self.daily_dose_kg()
        return round(daily / (conc / 100.0) * 1.2, 2)

    def contact_time_minutes(self, tank_volume_m3: float = 50.0) -> float:
        if self.water_flow_m3_h <= 0:
            return 0.0
        return round(tank_volume_m3 / self.water_flow_m3_h * 60, 1)

    def ct_value(self, tank_volume_m3: float = 50.0) -> float:
        return round(self.target_residual_mg_l * self.contact_time_minutes(tank_volume_m3), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "total_dose_mg_l": self.total_dose_mg_l(),
            "daily_dose_kg": self.daily_dose_kg(),
            "solution_volume_l_per_day": self.solution_volume_liters_per_day(),
        }

    def run(self):
        print("=" * 60)
        print("CHLORINE DOSE CALCULATOR")
        print("=" * 60)
        cl = ChlorineDose(
            water_flow_m3_h=500, chlorine_demand_mg_l=2.0,
            target_residual_mg_l=0.5, chlorine_type="hypochlorite_12"
        )
        print(f"Flow: {cl.water_flow_m3_h} m3/h")
        print(f"Demand: {cl.chlorine_demand_mg_l} mg/L")
        print(f"Total dose: {cl.total_dose_mg_l():.2f} mg/L")
        print(f"Daily dose: {cl.daily_dose_kg():.2f} kg")
        print(f"Solution volume: {cl.solution_volume_liters_per_day():.2f} L/day")
        print(f"Contact time: {cl.contact_time_minutes():.1f} min")
        print(f"CT value: {cl.ct_value():.2f}")
        print(f"Stats: {cl.stats()}")

if __name__ == "__main__":
    ChlorineDose(0, 0).run()
