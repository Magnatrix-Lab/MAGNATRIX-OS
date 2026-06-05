"""Native stdlib module: Crosswind Calculator
Calculates crosswind, headwind, and wind components for landing and takeoff.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class CrosswindCalculator:
    wind_direction_deg: float
    wind_speed_kts: float
    runway_heading_deg: float

    def wind_angle_relative(self) -> float:
        angle = self.wind_direction_deg - self.runway_heading_deg
        while angle > 180:
            angle -= 360
        while angle < -180:
            angle += 360
        return angle

    def crosswind_kts(self) -> float:
        return abs(self.wind_speed_kts * math.sin(math.radians(self.wind_angle_relative())))

    def headwind_kts(self) -> float:
        return self.wind_speed_kts * math.cos(math.radians(self.wind_angle_relative()))

    def tailwind_kts(self) -> float:
        hw = self.headwind_kts()
        return abs(hw) if hw < 0 else 0

    def effective_headwind_kts(self) -> float:
        hw = self.headwind_kts()
        return hw if hw > 0 else 0

    def crosswind_component_max(self, max_crosswind_kts: float) -> bool:
        return self.crosswind_kts() <= max_crosswind_kts

    def gust_adjusted_kts(self, gust_kts: float) -> float:
        return self.wind_speed_kts + (gust_kts - self.wind_speed_kts) * 0.5

    def stats(self) -> Dict:
        return {
            "wind_direction": self.wind_direction_deg,
            "wind_speed_kts": self.wind_speed_kts,
            "runway_heading": self.runway_heading_deg,
            "wind_angle_relative": round(self.wind_angle_relative(), 1),
            "crosswind_kts": round(self.crosswind_kts(), 1),
            "headwind_kts": round(self.effective_headwind_kts(), 1),
            "tailwind_kts": round(self.tailwind_kts(), 1),
        }

def run():
    cc = CrosswindCalculator(wind_direction_deg=270, wind_speed_kts=15, runway_heading_deg=300)
    print(cc.stats())

if __name__ == "__main__":
    run()
