"""Native stdlib module: Irrigation Calculator
Calculates water requirements, irrigation schedules, and efficiency.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class IrrigationMethod(Enum):
    DRIP = "drip"
    SPRINKLER = "sprinkler"
    FLOOD = "flood"
    PIVOT = "pivot"

@dataclass
class IrrigationCalculator:
    crop_name: str
    area_hectares: float
    etc_mm_per_day: float
    irrigation_method: IrrigationMethod
    efficiency_pct: float = 85.0
    days_between_irrigation: int = 7

    def daily_water_m3(self) -> float:
        area_m2 = self.area_hectares * 10000
        daily_mm = self.etc_mm_per_day / self.efficiency_pct * 100
        return area_m2 * (daily_mm / 1000)

    def irrigation_event_m3(self) -> float:
        return self.daily_water_m3() * self.days_between_irrigation

    def seasonal_water_m3(self, season_days: int = 120) -> float:
        return self.daily_water_m3() * season_days

    def stats(self) -> Dict:
        return {
            "crop": self.crop_name,
            "daily_water_m3": round(self.daily_water_m3(), 1),
            "per_irrigation_m3": round(self.irrigation_event_m3(), 1),
            "seasonal_water_m3": round(self.seasonal_water_m3(), 1),
            "method": self.irrigation_method.value,
        }

def run():
    ic = IrrigationCalculator(crop_name="Tomatoes", area_hectares=10, etc_mm_per_day=5, irrigation_method=IrrigationMethod.DRIP, efficiency_pct=90, days_between_irrigation=3)
    print(ic.stats())

if __name__ == "__main__":
    run()
