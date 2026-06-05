"""Native stdlib module: Drying Calculator
Calculates moisture removal rates, drying time, and energy for herbs and spices.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class DryingCalculator:
    initial_weight_g: float
    initial_moisture_pct: float
    target_moisture_pct: float
    drying_rate_g_per_hour: float

    def water_to_remove_g(self) -> float:
        return self.initial_weight_g * ((self.initial_moisture_pct - self.target_moisture_pct) / 100)

    def drying_time_hours(self) -> float:
        if self.drying_rate_g_per_hour <= 0:
            return 0.0
        return self.water_to_remove_g() / self.drying_rate_g_per_hour

    def final_weight_g(self) -> float:
        return self.initial_weight_g - self.water_to_remove_g()

    def shrinkage_pct(self) -> float:
        if self.initial_weight_g == 0:
            return 0.0
        return (self.water_to_remove_g() / self.initial_weight_g) * 100

    def stats(self) -> Dict[str, float]:
        return {
            "water_to_remove_g": round(self.water_to_remove_g(), 1),
            "drying_time_hours": round(self.drying_time_hours(), 1),
            "final_weight_g": round(self.final_weight_g(), 1),
            "shrinkage_pct": round(self.shrinkage_pct(), 1),
        }

def run():
    dc = DryingCalculator(initial_weight_g=1000, initial_moisture_pct=75, target_moisture_pct=10, drying_rate_g_per_hour=50)
    print(dc.stats())

if __name__ == "__main__":
    run()
