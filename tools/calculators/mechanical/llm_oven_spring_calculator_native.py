"""Native stdlib module: Oven Spring Calculator
Estimates bread expansion, steam needs, and baking temperature.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class OvenSpringCalculator:
    dough_weight_g: float
    hydration_pct: float
    oven_temp_c: float = 220.0
    steam_injection: bool = True
    loaf_shape: str = "batard"  # batard, boule, baguette, tin

    _EXPANSION_MULTIPLIERS = {
        "batard": 1.3, "boule": 1.2, "baguette": 1.5, "tin": 1.1,
    }

    def expansion_factor(self) -> float:
        base = self._EXPANSION_MULTIPLIERS.get(self.loaf_shape, 1.2)
        if self.hydration_pct > 70:
            base += 0.1
        if self.steam_injection:
            base += 0.15
        return base

    def estimated_baked_volume_ml(self) -> float:
        return self.dough_weight_g * self.expansion_factor()

    def oven_spring_pct(self) -> float:
        return (self.expansion_factor() - 1) * 100

    def steam_amount_ml(self) -> float:
        if not self.steam_injection:
            return 0
        return self.dough_weight_g * 0.05

    def initial_baking_temp_c(self) -> int:
        if self.loaf_shape == "baguette":
            return 240
        elif self.loaf_shape == "boule":
            return 230
        return 220

    def reduced_temp_after_spring_c(self) -> int:
        return self.initial_baking_temp_c() - 20

    def bake_time_min(self) -> float:
        base = 25
        if self.dough_weight_g > 1000:
            base += 15
        elif self.dough_weight_g > 500:
            base += 5
        if self.hydration_pct > 75:
            base += 5
        return base

    def crust_thickness_estimate_mm(self) -> float:
        if self.oven_temp_c > 230:
            return 4
        elif self.oven_temp_c > 210:
            return 3
        return 2

    def stats(self) -> Dict:
        return {
            "dough_weight_g": self.dough_weight_g,
            "hydration_pct": self.hydration_pct,
            "loaf_shape": self.loaf_shape,
            "expansion_factor": round(self.expansion_factor(), 2),
            "oven_spring_pct": round(self.oven_spring_pct(), 1),
            "estimated_baked_volume_ml": round(self.estimated_baked_volume_ml(), 1),
            "steam_amount_ml": round(self.steam_amount_ml(), 1),
            "initial_baking_temp_c": self.initial_baking_temp_c(),
            "reduced_temp_after_spring_c": self.reduced_temp_after_spring_c(),
            "bake_time_min": self.bake_time_min(),
            "crust_thickness_estimate_mm": self.crust_thickness_estimate_mm(),
        }

def run():
    osc = OvenSpringCalculator(dough_weight_g=800, hydration_pct=72, oven_temp_c=230, steam_injection=True, loaf_shape="boule")
    print(osc.stats())

if __name__ == "__main__":
    run()
