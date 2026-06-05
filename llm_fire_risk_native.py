"""Fire Risk — FWI, fuel moisture, spread rate, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class FireRisk:
    temperature: float = 30.0
    humidity: float = 30.0
    wind_speed: float = 20.0
    precipitation: float = 0.0
    fuel_moisture: float = 10.0

    def fire_weather_index(self) -> float:
        """Simplified FWI component"""
        isi = 0.208 * self.wind_speed * (100 - self.humidity) / 100 * (100 - self.fuel_moisture) / 100
        bui = max(0, 0.1 * self.temperature * (100 - self.humidity) / 100 - self.precipitation)
        return isi * bui / 100

    def rate_of_spread(self) -> float:
        fwi = self.fire_weather_index()
        return 0.5 * fwi * (1 + self.wind_speed / 10)

    def fire_danger_rating(self) -> str:
        fwi = self.fire_weather_index()
        if fwi < 5: return "low"
        elif fwi < 15: return "moderate"
        elif fwi < 30: return "high"
        elif fwi < 50: return "very high"
        return "extreme"

    def critical_fire_weather(self) -> bool:
        return self.humidity < 20 and self.wind_speed > 25 and self.temperature > 35

    def stats(self) -> Dict:
        return {"fwi": round(self.fire_weather_index(), 2), "ros": round(self.rate_of_spread(), 2), "danger": self.fire_danger_rating(), "critical": self.critical_fire_weather()}

def run():
    fr = FireRisk(temperature=38, humidity=15, wind_speed=30, fuel_moisture=5)
    print(fr.stats())

if __name__ == "__main__":
    run()
