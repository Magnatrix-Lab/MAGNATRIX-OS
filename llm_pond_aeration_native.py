"""Pond Aeration Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PondAeration:
    pond_area_sqm: float
    pond_depth_m: float
    fish_biomass_kg: float
    water_temp_c: float = 25.0
    dissolved_oxygen_mg_l: float = 6.0

    def pond_volume_m3(self) -> float:
        return round(self.pond_area_sqm * self.pond_depth_m, 1)

    def oxygen_demand_kg_per_day(self) -> float:
        fish_demand = self.fish_biomass_kg * 0.02
        temp_factor = 1 + (self.water_temp_c - 20) / 20.0
        return round(fish_demand * temp_factor, 2)

    def oxygen_supply_kg_per_day(self) -> float:
        sat_do = 8.0 - (self.water_temp_c - 20) * 0.15
        transfer = 0.5
        return round(self.pond_area_sqm * transfer * sat_do / 1000.0, 2)

    def oxygen_deficit_kg_per_day(self) -> float:
        return round(self.oxygen_demand_kg_per_day() - self.oxygen_supply_kg_per_day(), 2)

    def aeration_required_kg_o2_per_h(self) -> float:
        deficit = self.oxygen_deficit_kg_per_day()
        if deficit <= 0:
            return 0.0
        return round(deficit / 24, 3)

    def aerator_power_kw(self, aerator_efficiency_kg_o2_per_kwh: float = 1.5) -> float:
        if aerator_efficiency_kg_o2_per_kwh <= 0:
            return 0.0
        return round(self.aeration_required_kg_o2_per_h() / aerator_efficiency_kg_o2_per_kwh, 2)

    def turnover_time_hours(self, flow_rate_m3_h: float = 100.0) -> float:
        vol = self.pond_volume_m3()
        if flow_rate_m3_h <= 0:
            return 0.0
        return round(vol / flow_rate_m3_h, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "pond_volume_m3": self.pond_volume_m3(),
            "oxygen_demand_kg_per_day": self.oxygen_demand_kg_per_day(),
            "oxygen_deficit_kg_per_day": self.oxygen_deficit_kg_per_day(),
        }

    def run(self):
        print("=" * 60)
        print("POND AERATION CALCULATOR")
        print("=" * 60)
        pa = PondAeration(
            pond_area_sqm=1000, pond_depth_m=1.5, fish_biomass_kg=2000, water_temp_c=28
        )
        print(f"Pond: {pa.pond_area_sqm} sqm x {pa.pond_depth_m} m")
        print(f"Volume: {pa.pond_volume_m3():.1f} m3")
        print(f"O2 demand: {pa.oxygen_demand_kg_per_day():.2f} kg/day")
        print(f"O2 supply: {pa.oxygen_supply_kg_per_day():.2f} kg/day")
        print(f"O2 deficit: {pa.oxygen_deficit_kg_per_day():.2f} kg/day")
        print(f"Aeration req: {pa.aeration_required_kg_o2_per_h():.3f} kg O2/h")
        print(f"Aerator power: {pa.aerator_power_kw():.2f} kW")
        print(f"Stats: {pa.stats()}")

if __name__ == "__main__":
    PondAeration(0, 0, 0).run()
