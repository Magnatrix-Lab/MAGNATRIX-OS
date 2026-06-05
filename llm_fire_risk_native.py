"""Fire Risk Calculator — fuel, weather, slope, ignition probability, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class FireRisk:
    fuel_moisture: float = 10.0
    wind_speed: float = 20.0
    temperature: float = 30.0
    slope_pct: float = 15.0
    fuel_load: float = 5.0

    def fire_weather_index(self) -> float:
        return (self.temperature + self.wind_speed) / (self.fuel_moisture + 1)

    def rate_of_spread(self) -> float:
        return 0.5 * self.wind_speed * (1 + self.slope_pct / 100) / (self.fuel_moisture + 1)

    def fire_danger_rating(self) -> str:
        fwi = self.fire_weather_index()
        if fwi < 5: return "low"
        elif fwi < 10: return "moderate"
        elif fwi < 20: return "high"
        elif fwi < 30: return "very high"
        return "extreme"

    def ignition_probability(self) -> float:
        base = 0.1
        if self.temperature > 35: base += 0.2
        if self.fuel_moisture < 8: base += 0.3
        if self.wind_speed > 30: base += 0.2
        return min(1.0, base)

    def stats(self) -> Dict:
        return {"fwi": round(self.fire_weather_index(), 2), "ros": round(self.rate_of_spread(), 2), "danger": self.fire_danger_rating(), "ignition_prob": round(self.ignition_probability(), 2)}

def run():
    fr = FireRisk(fuel_moisture=5, wind_speed=40, temperature=38, slope_pct=25)
    print(fr.stats())

if __name__ == "__main__":
    run()
