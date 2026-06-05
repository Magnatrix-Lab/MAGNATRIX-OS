"""Native stdlib module: Candy Sugar Calculator
Calculates sugar stages, temperatures, and final hardness.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CandySugarCalculator:
    sugar_weight_g: float
    water_weight_g: float
    target_stage: str  # thread, soft_ball, firm_ball, hard_ball, soft_crack, hard_crack, caramel
    altitude_m: float = 0.0

    _STAGE_TEMPS = {
        "thread": 110, "soft_ball": 115, "firm_ball": 118,
        "hard_ball": 121, "soft_crack": 132, "hard_crack": 146, "caramel": 170,
    }

    def target_temp_c(self) -> int:
        return self._STAGE_TEMPS.get(self.target_stage, 115)

    def adjusted_temp_c(self) -> float:
        return self.target_temp_c() - (self.altitude_m / 300)

    def concentration_pct(self) -> float:
        total = self.sugar_weight_g + self.water_weight_g
        if total == 0:
            return 0
        return (self.sugar_weight_g / total) * 100

    def final_moisture_pct(self) -> float:
        stages = {
            "thread": 8, "soft_ball": 5, "firm_ball": 4,
            "hard_ball": 3, "soft_crack": 2, "hard_crack": 1, "caramel": 0.5,
        }
        return stages.get(self.target_stage, 5)

    def hardness(self) -> str:
        return self.target_stage

    def boiling_time_estimate_min(self) -> float:
        if self.water_weight_g == 0:
            return 0
        return (self.water_weight_g / 100) * 5 + (self.target_temp_c() - 100) * 0.3

    def test_method(self) -> str:
        methods = {
            "thread": "spin_a_thread",
            "soft_ball": "drop_in_cold_water_and_form_soft_ball",
            "firm_ball": "drop_in_cold_water_and_form_firm_ball",
            "hard_ball": "drop_in_cold_water_and_form_hard_ball",
            "soft_crack": "drop_in_cold_water_and_separate_into_soft_threads",
            "hard_crack": "drop_in_cold_water_and_separate_into_hard_threads",
            "caramel": "amber_color",
        }
        return methods.get(self.target_stage, "thermometer")

    def stats(self) -> Dict:
        return {
            "sugar_weight_g": self.sugar_weight_g,
            "water_weight_g": self.water_weight_g,
            "target_stage": self.target_stage,
            "target_temp_c": self.target_temp_c(),
            "adjusted_temp_c": round(self.adjusted_temp_c(), 1),
            "concentration_pct": round(self.concentration_pct(), 1),
            "final_moisture_pct": self.final_moisture_pct(),
            "boiling_time_estimate_min": round(self.boiling_time_estimate_min(), 1),
            "test_method": self.test_method(),
        }

def run():
    csc = CandySugarCalculator(sugar_weight_g=500, water_weight_g=150, target_stage="hard_ball", altitude_m=500)
    print(csc.stats())

if __name__ == "__main__":
    run()
