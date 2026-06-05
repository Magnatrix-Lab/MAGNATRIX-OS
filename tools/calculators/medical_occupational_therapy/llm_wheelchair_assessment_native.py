"""Native stdlib module: Wheelchair Assessment Calculator
Calculates wheelchair fit, pressure distribution, and propulsion efficiency.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class WheelchairType(Enum):
    MANUAL_STANDARD = "manual_standard"
    MANUAL_LIGHTWEIGHT = "manual_lightweight"
    MANUAL_ULTRALIGHT = "manual_ultralight"
    POWER_STANDARD = "power_standard"
    POWER_TILT = "power_tilt"

@dataclass
class WheelchairAssessmentCalculator:
    patient_weight_kg: float
    patient_height_cm: float
    seat_width_in: float
    seat_depth_in: float
    back_height_in: float
    wheelchair_type: WheelchairType
    rear_wheel_diameter_in: float = 24.0

    def recommended_seat_width_in(self) -> float:
        return (self.patient_weight_kg ** 0.33) * 2.5

    def recommended_seat_depth_in(self) -> float:
        return (self.patient_height_cm / 2.54) * 0.25

    def seat_width_fit(self) -> str:
        diff = self.seat_width_in - self.recommended_seat_width_in()
        if diff < -1:
            return "too_narrow"
        elif diff > 2:
            return "too_wide"
        return "appropriate"

    def seat_depth_fit(self) -> str:
        diff = self.seat_depth_in - self.recommended_seat_depth_in()
        if diff < -1:
            return "too_shallow"
        elif diff > 2:
            return "too_deep"
        return "appropriate"

    def pressure_ulcer_risk(self) -> str:
        if self.seat_width_fit() != "appropriate" or self.seat_depth_fit() != "appropriate":
            return "elevated"
        return "standard"

    def push_rim_force_lbs(self) -> float:
        if self.rear_wheel_diameter_in == 0:
            return 0.0
        return (self.patient_weight_kg * 2.2) / (self.rear_wheel_diameter_in / 2) * 3

    def propulsion_strokes_per_min(self, speed_mph: float = 3) -> float:
        if self.rear_wheel_diameter_in == 0:
            return 0.0
        circumference_ft = (self.rear_wheel_diameter_in * math.pi) / 12
        speed_fpm = speed_mph * 88
        return speed_fpm / circumference_ft

    def stats(self) -> Dict:
        return {
            "wheelchair_type": self.wheelchair_type.value,
            "recommended_seat_width_in": round(self.recommended_seat_width_in(), 1),
            "actual_seat_width_in": self.seat_width_in,
            "seat_width_fit": self.seat_width_fit(),
            "recommended_seat_depth_in": round(self.recommended_seat_depth_in(), 1),
            "actual_seat_depth_in": self.seat_depth_in,
            "seat_depth_fit": self.seat_depth_fit(),
            "pressure_ulcer_risk": self.pressure_ulcer_risk(),
            "push_rim_force_lbs": round(self.push_rim_force_lbs(), 1),
        }

def run():
    import math
    wac = WheelchairAssessmentCalculator(patient_weight_kg=75, patient_height_cm=170, seat_width_in=18, seat_depth_in=16, back_height_in=16, wheelchair_type=WheelchairType.MANUAL_ULTRALIGHT, rear_wheel_diameter_in=24)
    print(wac.stats())

if __name__ == "__main__":
    run()
