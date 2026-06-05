"""Native stdlib module: Fire Risk Calculator
Calculates fire weather indices, fire behavior, and suppression metrics.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class FuelType(Enum):
    GRASS = "grass"
    SHRUB = "shrub"
    FOREST = "forest"
    LOGGING_DEBRIS = "logging_debris"

@dataclass
class FireRiskCalculator:
    temperature_c: float
    relative_humidity_pct: float
    wind_speed_kmh: float
    precipitation_mm: float
    fuel_type: FuelType
    fuel_load_ton_ha: float

    def fire_weather_index(self) -> float:
        if self.precipitation_mm > 2:
            return 0.0
        fwi = (self.temperature_c * (100 - self.relative_humidity_pct) * self.wind_speed_kmh) / 100
        return max(0, fwi)

    def rate_of_spread_m_min(self) -> float:
        if self.fire_weather_index() == 0:
            return 0.0
        ros_factors = {FuelType.GRASS: 2.0, FuelType.SHRUB: 1.5, FuelType.FOREST: 0.8, FuelType.LOGGING_DEBRIS: 1.2}
        return self.fire_weather_index() * ros_factors.get(self.fuel_type, 1.0) / 10

    def fire_intensity_kw_m(self) -> float:
        return self.rate_of_spread_m_min() * 60 * self.fuel_load_ton_ha * 18000 / 10000

    def flame_length_m(self) -> float:
        if self.fire_intensity_kw_m() == 0:
            return 0.0
        return 0.0775 * (self.fire_intensity_kw_m() ** 0.46)

    def suppression_difficulty(self) -> str:
        if self.fire_intensity_kw_m() < 100:
            return "low"
        elif self.fire_intensity_kw_m() < 1000:
            return "moderate"
        elif self.fire_intensity_kw_m() < 3000:
            return "high"
        return "extreme"

    def stats(self) -> Dict:
        return {
            "fire_weather_index": round(self.fire_weather_index(), 1),
            "rate_of_spread_m_min": round(self.rate_of_spread_m_min(), 2),
            "fire_intensity_kw_m": round(self.fire_intensity_kw_m(), 1),
            "flame_length_m": round(self.flame_length_m(), 1),
            "suppression_difficulty": self.suppression_difficulty(),
        }

def run():
    frc = FireRiskCalculator(temperature_c=32, relative_humidity_pct=25, wind_speed_kmh=25, precipitation_mm=0, fuel_type=FuelType.FOREST, fuel_load_ton_ha=15)
    print(frc.stats())

if __name__ == "__main__":
    run()
