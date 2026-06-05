"""Native stdlib module: Coffee Roast Profile Calculator
Calculates roast curves, development time, and color targets.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CoffeeRoastProfileCalculator:
    batch_size_kg: float
    green_moisture_pct: float = 10.0
    target_roast_level: str = "medium"  # light, medium, medium_dark, dark
    roaster_type: str = "drum"  # drum, air, fluid_bed

    _ROAST_TIMES = {
        "light": 10, "medium": 12, "medium_dark": 14, "dark": 16,
    }

    _DROP_TEMPS = {
        "light": 205, "medium": 215, "medium_dark": 225, "dark": 235,
    }

    def roast_time_min(self) -> float:
        return self._ROAST_TIMES.get(self.target_roast_level, 12) + self.batch_size_kg * 0.5

    def drop_temp_c(self) -> int:
        return self._DROP_TEMPS.get(self.target_roast_level, 215)

    def first_crack_time_min(self) -> float:
        return self.roast_time_min() * 0.75

    def development_time_pct(self) -> float:
        return (self.roast_time_min() - self.first_crack_time_min()) / self.roast_time_min() * 100

    def development_ratio(self) -> float:
        return (self.roast_time_min() - self.first_crack_time_min()) / self.first_crack_time_min()

    def weight_loss_pct(self) -> float:
        return self.green_moisture_pct + 2 + (self._DROP_TEMPS.get(self.target_roast_level, 215) - 200) * 0.1

    def roasted_weight_kg(self) -> float:
        return self.batch_size_kg * (1 - self.weight_loss_pct() / 100)

    def color_target_agtron(self) -> int:
        colors = {"light": 75, "medium": 55, "medium_dark": 45, "dark": 35}
        return colors.get(self.target_roast_level, 55)

    def stats(self) -> Dict:
        return {
            "batch_size_kg": self.batch_size_kg,
            "target_roast_level": self.target_roast_level,
            "roast_time_min": round(self.roast_time_min(), 1),
            "drop_temp_c": self.drop_temp_c(),
            "first_crack_time_min": round(self.first_crack_time_min(), 1),
            "development_time_pct": round(self.development_time_pct(), 1),
            "development_ratio": round(self.development_ratio(), 2),
            "weight_loss_pct": round(self.weight_loss_pct(), 1),
            "roasted_weight_kg": round(self.roasted_weight_kg(), 2),
            "color_target_agtron": self.color_target_agtron(),
        }

def run():
    crpc = CoffeeRoastProfileCalculator(batch_size_kg=5, green_moisture_pct=11, target_roast_level="medium")
    print(crpc.stats())

if __name__ == "__main__":
    run()
