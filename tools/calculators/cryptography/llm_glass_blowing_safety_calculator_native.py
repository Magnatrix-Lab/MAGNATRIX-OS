"""Native stdlib module: Glass Blowing Safety Calculator
Calculates ventilation needs, heat exposure limits, and safety margins.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class GlassBlowingSafetyCalculator:
    studio_area_m2: float
    ceiling_height_m: float
    furnaces_count: int
    furnace_total_kw: float
    people_count: int = 2

    def studio_volume_m3(self) -> float:
        return self.studio_area_m2 * self.ceiling_height_m

    def required_ventilation_m3_per_hour(self) -> float:
        return self.studio_volume_m3() * 6

    def heat_gain_kw(self) -> float:
        return self.furnace_total_kw * 0.7

    def heat_gain_per_person_kw(self) -> float:
        return self.people_count * 0.1

    def total_heat_load_kw(self) -> float:
        return self.heat_gain_kw() + self.heat_gain_per_person_kw()

    def temperature_rise_c(self) -> float:
        air_density = 1.2
        cp = 1.005
        if self.required_ventilation_m3_per_hour() == 0:
            return 0
        return (self.total_heat_load_kw() * 3600) / (self.required_ventilation_m3_per_hour() * air_density * cp)

    def heat_stress_risk(self) -> str:
        rise = self.temperature_rise_c()
        if rise < 3:
            return "low"
        elif rise < 6:
            return "moderate"
        elif rise < 10:
            return "high"
        return "extreme"

    def recommended_break_minutes_per_hour(self) -> int:
        rise = self.temperature_rise_c()
        if rise < 3:
            return 0
        elif rise < 6:
            return 10
        elif rise < 10:
            return 20
        return 30

    def stats(self) -> Dict:
        return {
            "studio_volume_m3": round(self.studio_volume_m3(), 1),
            "required_ventilation_m3_h": round(self.required_ventilation_m3_per_hour(), 1),
            "total_heat_load_kw": round(self.total_heat_load_kw(), 1),
            "temperature_rise_c": round(self.temperature_rise_c(), 1),
            "heat_stress_risk": self.heat_stress_risk(),
            "recommended_break_min_per_hour": self.recommended_break_minutes_per_hour(),
        }

def run():
    gbsc = GlassBlowingSafetyCalculator(studio_area_m2=50, ceiling_height_m=4, furnaces_count=3, furnace_total_kw=45)
    print(gbsc.stats())

if __name__ == "__main__":
    run()
