"""Native stdlib module: Tea Steeping Calculator
Calculates optimal temperature, time, and leaf-to-water ratios for tea.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class TeaSteepingCalculator:
    tea_type: str  # green, white, oolong, black, puerh, herbal
    leaf_weight_g: float = 3.0
    water_volume_ml: float = 250.0

    _TEMPERATURES = {
        "green": 75, "white": 80, "oolong": 90, "black": 95, "puerh": 95, "herbal": 100,
    }

    _TIMES = {
        "green": 2, "white": 3, "oolong": 3, "black": 4, "puerh": 5, "herbal": 5,
    }

    def recommended_temp_c(self) -> int:
        return self._TEMPERATURES.get(self.tea_type, 85)

    def recommended_time_min(self) -> float:
        return self._TIMES.get(self.tea_type, 3)

    def leaf_to_water_ratio(self) -> float:
        if self.water_volume_ml == 0:
            return 0
        return self.leaf_weight_g / self.water_volume_ml

    def ratio_g_per_l(self) -> float:
        if self.water_volume_ml == 0:
            return 0
        return (self.leaf_weight_g / self.water_volume_ml) * 1000

    def western_vs_gongfu(self) -> str:
        if self.ratio_g_per_l() < 5:
            return "western_style"
        elif self.ratio_g_per_l() < 10:
            return "balanced"
        return "gongfu_style"

    def multiple_infusions(self) -> int:
        infusions = {"green": 3, "white": 4, "oolong": 7, "black": 4, "puerh": 10, "herbal": 2}
        return infusions.get(self.tea_type, 3)

    def time_increase_per_infusion_pct(self) -> float:
        increases = {"green": 20, "white": 15, "oolong": 10, "black": 20, "puerh": 10, "herbal": 30}
        return increases.get(self.tea_type, 20)

    def stats(self) -> Dict:
        return {
            "tea_type": self.tea_type,
            "recommended_temp_c": self.recommended_temp_c(),
            "recommended_time_min": self.recommended_time_min(),
            "leaf_to_water_ratio": round(self.leaf_to_water_ratio(), 3),
            "ratio_g_per_l": round(self.ratio_g_per_l(), 1),
            "brewing_style": self.western_vs_gongfu(),
            "multiple_infusions": self.multiple_infusions(),
            "time_increase_per_infusion_pct": self.time_increase_per_infusion_pct(),
        }

def run():
    tsc = TeaSteepingCalculator(tea_type="oolong", leaf_weight_g=5, water_volume_ml=150)
    print(tsc.stats())

if __name__ == "__main__":
    run()
