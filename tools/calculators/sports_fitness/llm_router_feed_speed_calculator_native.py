"""Native stdlib module: Router Feed Speed Calculator
Calculates feed rates, RPM, chip load, and cutting speeds.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class RouterFeedSpeedCalculator:
    bit_diameter_in: float
    number_of_flutes: int = 2
    spindle_speed_rpm: float = 18000.0
    chip_load_per_tooth_in: float = 0.005
    cut_depth_in: float = 0.25

    def feed_rate_ipm(self) -> float:
        return self.spindle_speed_rpm * self.number_of_flutes * self.chip_load_per_tooth_in

    def chip_load_actual(self) -> float:
        if self.spindle_speed_rpm == 0 or self.number_of_flutes == 0:
            return 0
        return self.feed_rate_ipm() / (self.spindle_speed_rpm * self.number_of_flutes)

    def surface_speed_sfm(self) -> float:
        return (self.bit_diameter_in * 3.14159 * self.spindle_speed_rpm) / 12

    def recommended_rpm(self, max_sfm: float = 500) -> float:
        if self.bit_diameter_in == 0:
            return 0
        return (max_sfm * 12) / (self.bit_diameter_in * 3.14159)

    def material_removal_rate_in3_per_min(self) -> float:
        return self.feed_rate_ipm() * self.bit_diameter_in * self.cut_depth_in

    def cut_quality_estimate(self) -> str:
        cl = self.chip_load_actual()
        if cl < 0.003:
            return "burning_risk"
        elif cl < 0.007:
            return "good"
        elif cl < 0.012:
            return "rough"
        return "chipping_risk"

    def stats(self) -> Dict:
        return {
            "bit_diameter_in": self.bit_diameter_in,
            "feed_rate_ipm": round(self.feed_rate_ipm(), 1),
            "chip_load_actual_in": round(self.chip_load_actual(), 4),
            "surface_speed_sfm": round(self.surface_speed_sfm(), 1),
            "recommended_rpm": round(self.recommended_rpm(), 0),
            "material_removal_rate_in3_min": round(self.material_removal_rate_in3_per_min(), 3),
            "cut_quality": self.cut_quality_estimate(),
        }

def run():
    rfsc = RouterFeedSpeedCalculator(bit_diameter_in=0.5, number_of_flutes=2, spindle_speed_rpm=20000, chip_load_per_tooth_in=0.004, cut_depth_in=0.125)
    print(rfsc.stats())

if __name__ == "__main__":
    run()
