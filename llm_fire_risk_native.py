"""Fire Risk Calculator — weather, fuel, topography, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class FireRiskCalculator:
    temperature: float = 30.0
    humidity: float = 20.0
    wind_speed: float = 25.0
    fuel_moisture: float = 8.0
    slope_pct: float = 15.0

    def ffdi(self) -> float:
        """Forest Fire Danger Index (McArthur)."""
        df = 2 * (self.temperature - 20) + 0.5 * self.humidity
        if df < 0:
            df = 0
        k = 0.5 + 0.03 * self.wind_speed
        return df * k * max(1, self.slope_pct / 10)

    def danger_rating(self) -> str:
        ffdi = self.ffdi()
        if ffdi < 12: return "low"
        elif ffdi < 24: return "moderate"
        elif ffdi < 50: return "high"
        elif ffdi < 100: return "very high"
        return "extreme"

    def rate_of_spread(self) -> float:
        """km/h approximation."""
        return 0.5 * self.ffdi() ** 0.5

    def spotting_distance(self) -> float:
        return 0.5 * self.wind_speed * (self.ffdi() / 50) ** 0.5

    def suppression_difficulty(self) -> float:
        return min(1.0, self.ffdi() / 100 + self.slope_pct / 100)

    def stats(self) -> Dict:
        return {"ffdi": round(self.ffdi(), 1), "rating": self.danger_rating(), "ros_kmh": round(self.rate_of_spread(), 2)}

def run():
    frc = FireRiskCalculator(temperature=38, humidity=12, wind_speed=40, slope_pct=25)
    print(frc.stats())

if __name__ == "__main__":
    run()
