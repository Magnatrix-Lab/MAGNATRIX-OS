"""Native stdlib module: Track Gauge Calculator
Calculates rail gauge compatibility, curve radii, and superelevation for railroads.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class GaugeType(Enum):
    STANDARD = 1435
    BROAD = 1676
    NARROW = 1067
    METER = 1000

@dataclass
class TrackGaugeCalculator:
    gauge_type: GaugeType
    curve_radius_m: float
    design_speed_kmh: float
    cant_mm: float = 0.0

    def superelevation_mm(self) -> float:
        if self.curve_radius_m == 0:
            return 0.0
        return (11.8 * self.design_speed_kmh**2) / self.curve_radius_m

    def cant_deficiency_mm(self) -> float:
        return max(0, self.superelevation_mm() - self.cant_mm)

    def cant_excess_mm(self) -> float:
        return max(0, self.cant_mm - self.superelevation_mm())

    def max_speed_kmh(self) -> float:
        if self.curve_radius_m == 0:
            return 0.0
        return ((self.cant_mm * self.curve_radius_m) / 11.8) ** 0.5

    def transition_length_m(self, max_gradient: float = 1/150) -> float:
        if max_gradient == 0:
            return 0.0
        return self.cant_mm / (max_gradient * 1000)

    def stats(self) -> Dict:
        return {
            "gauge_mm": self.gauge_type.value,
            "curve_radius_m": self.curve_radius_m,
            "design_speed_kmh": self.design_speed_kmh,
            "superelevation_mm": round(self.superelevation_mm(), 1),
            "cant_deficiency_mm": round(self.cant_deficiency_mm(), 1),
            "max_speed_kmh": round(self.max_speed_kmh(), 1),
            "transition_length_m": round(self.transition_length_m(), 1),
        }

def run():
    tgc = TrackGaugeCalculator(gauge_type=GaugeType.STANDARD, curve_radius_m=800, design_speed_kmh=120, cant_mm=100)
    print(tgc.stats())

if __name__ == "__main__":
    run()
