"""Native stdlib module: Tanning Solution Calculator
Calculates tannin concentration, pH, liquor ratio, and solution volumes.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class TanningSolutionCalculator:
    hide_weight_kg: float
    tan_type: str  # vegetable, chrome, alum, brain, oil
    liquor_ratio: float = 2.0  # liquor volume : hide weight
    desired_tannin_pct: float = 20.0

    _TAN_PROPERTIES = {
        "vegetable": {"ph_range": (3.5, 4.5), "tanning_time_days": 30, "tanning_pct": 25},
        "chrome": {"ph_range": (3.0, 3.5), "tanning_time_days": 1, "tanning_pct": 15},
        "alum": {"ph_range": (3.0, 4.0), "tanning_time_days": 7, "tanning_pct": 10},
        "brain": {"ph_range": (6.0, 7.0), "tanning_time_days": 3, "tanning_pct": 5},
        "oil": {"ph_range": (6.0, 7.0), "tanning_time_days": 14, "tanning_pct": 8},
    }

    def liquor_volume_l(self) -> float:
        return self.hide_weight_kg * self.liquor_ratio

    def tannin_weight_kg(self) -> float:
        return self.liquor_volume_l() * (self.desired_tannin_pct / 100)

    def recommended_ph_range(self) -> tuple:
        return self._TAN_PROPERTIES.get(self.tan_type, {}).get("ph_range", (3.5, 4.5))

    def tanning_time_days(self) -> int:
        return self._TAN_PROPERTIES.get(self.tan_type, {}).get("tanning_time_days", 14)

    def tannin_pct_recommended(self) -> float:
        return self._TAN_PROPERTIES.get(self.tan_type, {}).get("tanning_pct", 20)

    def solution_strength_check(self) -> str:
        rec = self.tannin_pct_recommended()
        if self.desired_tannin_pct < rec * 0.7:
            return "too_weak"
        elif self.desired_tannin_pct > rec * 1.3:
            return "too_strong"
        return "appropriate"

    def stats(self) -> Dict:
        return {
            "hide_weight_kg": self.hide_weight_kg,
            "tan_type": self.tan_type,
            "liquor_volume_l": round(self.liquor_volume_l(), 1),
            "tannin_weight_kg": round(self.tannin_weight_kg(), 3),
            "desired_tannin_pct": self.desired_tannin_pct,
            "recommended_ph_range": self.recommended_ph_range(),
            "tanning_time_days": self.tanning_time_days(),
            "recommended_tannin_pct": self.tannin_pct_recommended(),
            "solution_strength": self.solution_strength_check(),
        }

def run():
    tsc = TanningSolutionCalculator(hide_weight_kg=5, tan_type="vegetable", liquor_ratio=2.5, desired_tannin_pct=22)
    print(tsc.stats())

if __name__ == "__main__":
    run()
