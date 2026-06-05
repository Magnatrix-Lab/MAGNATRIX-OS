"""Native stdlib module: Nib Size Calculator
Calculates nib sizes, line weights, and x-height ratios for calligraphy.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import math

@dataclass
class NibSizeCalculator:
    nib_width_mm: float
    pen_angle_deg: float = 45.0
    x_height_mm: float = 4.0

    def nib_height_mm(self) -> float:
        return self.nib_width_mm / math.sin(math.radians(self.pen_angle_deg))

    def line_weight_min_mm(self) -> float:
        return self.nib_width_mm * math.sin(math.radians(self.pen_angle_deg))

    def line_weight_max_mm(self) -> float:
        return self.nib_width_mm

    def stroke_width_hairline_mm(self) -> float:
        return self.nib_width_mm * 0.1

    def stroke_ratio(self) -> float:
        if self.line_weight_min_mm() == 0:
            return 0
        return self.line_weight_max_mm() / self.line_weight_min_mm()

    def x_height_to_nib_ratio(self) -> float:
        if self.nib_width_mm == 0:
            return 0
        return self.x_height_mm / self.nib_width_mm

    def ascender_height_mm(self) -> float:
        return self.x_height_mm * 1.5

    def descender_height_mm(self) -> float:
        return self.x_height_mm * 0.5

    def stats(self) -> Dict:
        return {
            "nib_width_mm": self.nib_width_mm,
            "pen_angle_deg": self.pen_angle_deg,
            "line_weight_min_mm": round(self.line_weight_min_mm(), 2),
            "line_weight_max_mm": round(self.line_weight_max_mm(), 2),
            "stroke_ratio": round(self.stroke_ratio(), 1),
            "x_height_to_nib_ratio": round(self.x_height_to_nib_ratio(), 1),
            "ascender_height_mm": round(self.ascender_height_mm(), 1),
            "descender_height_mm": round(self.descender_height_mm(), 1),
        }

def run():
    nsc = NibSizeCalculator(nib_width_mm=2.4, pen_angle_deg=45, x_height_mm=5)
    print(nsc.stats())

if __name__ == "__main__":
    run()
