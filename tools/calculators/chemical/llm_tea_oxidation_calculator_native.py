"""Native stdlib module: Tea Oxidation Calculator
Calculates oxidation levels, withering time, and enzymatic activity.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class TeaOxidationCalculator:
    tea_type: str  # green, white, yellow, oolong, black, dark
    leaf_weight_kg: float = 1.0
    withering_time_hours: Optional[float] = None
    rolling_time_min: Optional[float] = None

    _OXIDATION_PCT = {
        "green": 0, "white": 5, "yellow": 10, "oolong": 50, "black": 100, "dark": 100,
    }

    _WITHERING_HOURS = {
        "green": 0, "white": 24, "yellow": 6, "oolong": 18, "black": 18, "dark": 36,
    }

    def oxidation_pct(self) -> float:
        return self._OXIDATION_PCT.get(self.tea_type, 50)

    def recommended_withering_hours(self) -> float:
        return self._WITHERING_HOURS.get(self.tea_type, 18)

    def actual_withering_hours(self) -> float:
        if self.withering_time_hours is not None:
            return self.withering_time_hours
        return self.recommended_withering_hours()

    def withering_loss_pct(self) -> float:
        return min(30, self.actual_withering_hours() * 1.5)

    def rolling_time_recommended_min(self) -> float:
        times = {"green": 20, "white": 10, "yellow": 30, "oolong": 60, "black": 90, "dark": 120}
        return times.get(self.tea_type, 60)

    def fermentation_time_hours(self) -> float:
        if self.tea_type in ["black", "dark"]:
            return 2 + self.oxidation_pct() * 0.05
        return 0

    def drying_temp_c(self) -> int:
        temps = {"green": 120, "white": 100, "yellow": 110, "oolong": 130, "black": 90, "dark": 90}
        return temps.get(self.tea_type, 110)

    def stats(self) -> Dict:
        return {
            "tea_type": self.tea_type,
            "oxidation_pct": self.oxidation_pct(),
            "recommended_withering_hours": self.recommended_withering_hours(),
            "actual_withering_hours": self.actual_withering_hours(),
            "withering_loss_pct": round(self.withering_loss_pct(), 1),
            "rolling_time_recommended_min": self.rolling_time_recommended_min(),
            "fermentation_time_hours": round(self.fermentation_time_hours(), 1),
            "drying_temp_c": self.drying_temp_c(),
        }

def run():
    toc = TeaOxidationCalculator(tea_type="oolong", leaf_weight_kg=5, withering_time_hours=20, rolling_time_min=55)
    print(toc.stats())

if __name__ == "__main__":
    run()
