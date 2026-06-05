"""Native stdlib module: Timber Volume Calculator
Calculates log volume, board feet, and yield for forestry operations.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class LogRule(Enum):
    INTERNATIONAL_1_4 = "international_1_4"
    DOYLE = "doyle"
    SCRIBNER = "scribner"

@dataclass
class TimberVolumeCalculator:
    log_length_m: float
    small_end_diameter_cm: float
    large_end_diameter_cm: float
    log_rule: LogRule

    def log_volume_m3(self) -> float:
        avg_diameter = (self.small_end_diameter_cm + self.large_end_diameter_cm) / 2
        radius_m = (avg_diameter / 100) / 2
        return math.pi * (radius_m ** 2) * self.log_length_m

    def board_feet(self) -> float:
        d = self.small_end_diameter_cm / 2.54
        l = self.log_length_m / 0.3048
        if self.log_rule == LogRule.DOYLE:
            return ((d - 4) ** 2) * l / 16
        elif self.log_rule == LogRule.SCRIBNER:
            return (0.79 * d ** 2 - 2 * d - 4) * l / 16
        elif self.log_rule == LogRule.INTERNATIONAL_1_4:
            return 0.905 * ((d - 1) ** 2) * l / 16
        return 0.0

    def cubic_feet(self) -> float:
        return self.log_volume_m3() * 35.315

    def taper_cm_per_m(self) -> float:
        if self.log_length_m == 0:
            return 0.0
        return (self.large_end_diameter_cm - self.small_end_diameter_cm) / self.log_length_m

    def stats(self) -> Dict:
        return {
            "log_volume_m3": round(self.log_volume_m3(), 3),
            "board_feet": round(self.board_feet(), 1),
            "cubic_feet": round(self.cubic_feet(), 2),
            "taper_cm_per_m": round(self.taper_cm_per_m(), 2),
            "log_rule": self.log_rule.value,
        }

def run():
    import math
    tvc = TimberVolumeCalculator(log_length_m=6, small_end_diameter_cm=30, large_end_diameter_cm=40, log_rule=LogRule.INTERNATIONAL_1_4)
    print(tvc.stats())

if __name__ == "__main__":
    run()
