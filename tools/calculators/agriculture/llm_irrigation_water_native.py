"""Irrigation Water Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class IrrigationWater:
    crop_type: str
    area_ha: float
    et_rate_mm_per_day: float
    irrigation_efficiency: float = 70.0
    rainfall_mm_per_day: float = 0.0

    def water_requirement_mm_per_day(self) -> float:
        crop_factors = {"corn": 1.0, "wheat": 0.8, "rice": 1.2, "cotton": 1.1, "soybean": 0.9, "vegetables": 1.0}
        factor = crop_factors.get(self.crop_type, 1.0)
        return round(self.et_rate_mm_per_day * factor, 2)

    def net_water_requirement_mm_per_day(self) -> float:
        req = self.water_requirement_mm_per_day() - self.rainfall_mm_per_day
        return round(max(req, 0), 2)

    def gross_water_requirement_mm_per_day(self) -> float:
        net = self.net_water_requirement_mm_per_day()
        if self.irrigation_efficiency <= 0:
            return 0.0
        return round(net / (self.irrigation_efficiency / 100.0), 2)

    def water_volume_m3_per_day(self) -> float:
        mm = self.gross_water_requirement_mm_per_day()
        return round(mm * self.area_ha * 10000 / 1000.0, 1)

    def water_volume_liters_per_day(self) -> float:
        return round(self.water_volume_m3_per_day() * 1000, 0)

    def pump_capacity_required_m3_h(self, operating_hours: float = 12.0) -> float:
        if operating_hours <= 0:
            return 0.0
        return round(self.water_volume_m3_per_day() / operating_hours, 2)

    def irrigation_frequency_days(self, root_depth_mm: float = 300.0,
                                   available_water_capacity: float = 0.15) -> float:
        water_mm = root_depth_mm * available_water_capacity
        req = self.gross_water_requirement_mm_per_day()
        if req <= 0:
            return 0.0
        return round(water_mm / req, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "water_requirement_mm_per_day": self.water_requirement_mm_per_day(),
            "net_water_mm_per_day": self.net_water_requirement_mm_per_day(),
            "water_volume_m3_per_day": self.water_volume_m3_per_day(),
        }

    def run(self):
        print("=" * 60)
        print("IRRIGATION WATER CALCULATOR")
        print("=" * 60)
        irr = IrrigationWater(
            crop_type="corn", area_ha=20, et_rate_mm_per_day=6.0,
            irrigation_efficiency=75, rainfall_mm_per_day=2.0
        )
        print(f"Crop: {irr.crop_type}, Area: {irr.area_ha} ha")
        print(f"Water requirement: {irr.water_requirement_mm_per_day():.2f} mm/day")
        print(f"Net water: {irr.net_water_requirement_mm_per_day():.2f} mm/day")
        print(f"Gross water: {irr.gross_water_requirement_mm_per_day():.2f} mm/day")
        print(f"Volume: {irr.water_volume_m3_per_day():.1f} m3/day")
        print(f"Pump capacity: {irr.pump_capacity_required_m3_h():.2f} m3/h")
        print(f"Irrigation freq: {irr.irrigation_frequency_days():.1f} days")
        print(f"Stats: {irr.stats()}")

if __name__ == "__main__":
    IrrigationWater("corn", 0, 0).run()
