"""Native stdlib module: Calligraphy Guideline Calculator
Calculates ascender, descender, x-height ratios, and slant angles.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import math

@dataclass
class CalligraphyGuidelineCalculator:
    x_height_mm: float
    slant_angle_deg: float = 0.0
    script_style: str = "italic"  # italic, foundational, gothic, uncial

    _RATIOS = {
        "italic": {"ascender": 1.5, "descender": 0.5, "nib_ladder": 5},
        "foundational": {"ascender": 1.5, "descender": 0.5, "nib_ladder": 4},
        "gothic": {"ascender": 1.0, "descender": 0.5, "nib_ladder": 4},
        "uncial": {"ascender": 1.0, "descender": 0.0, "nib_ladder": 4},
    }

    def ascender_height_mm(self) -> float:
        ratio = self._RATIOS.get(self.script_style, {}).get("ascender", 1.5)
        return self.x_height_mm * ratio

    def descender_height_mm(self) -> float:
        ratio = self._RATIOS.get(self.script_style, {}).get("descender", 0.5)
        return self.x_height_mm * ratio

    def body_height_mm(self) -> float:
        return self.ascender_height_mm() + self.x_height_mm + self.descender_height_mm()

    def nib_ladder_count(self) -> int:
        return self._RATIOS.get(self.script_style, {}).get("nib_ladder", 5)

    def line_height_mm(self, leading: float = 1.5) -> float:
        return self.body_height_mm() * leading

    def slant_offset_mm(self, line_length_mm: float = 100.0) -> float:
        return line_length_mm * math.tan(math.radians(self.slant_angle_deg))

    def interline_spacing_mm(self, leading: float = 1.5) -> float:
        return self.line_height_mm(leading) - self.body_height_mm()

    def stats(self, line_length_mm: float = 100.0, leading: float = 1.5) -> Dict:
        return {
            "script_style": self.script_style,
            "x_height_mm": self.x_height_mm,
            "ascender_height_mm": round(self.ascender_height_mm(), 1),
            "descender_height_mm": round(self.descender_height_mm(), 1),
            "body_height_mm": round(self.body_height_mm(), 1),
            "line_height_mm": round(self.line_height_mm(leading), 1),
            "interline_spacing_mm": round(self.interline_spacing_mm(leading), 1),
            "slant_angle_deg": self.slant_angle_deg,
            "slant_offset_mm": round(self.slant_offset_mm(line_length_mm), 1),
            "nib_ladder_count": self.nib_ladder_count(),
        }

def run():
    cgc = CalligraphyGuidelineCalculator(x_height_mm=5, slant_angle_deg=8, script_style="italic")
    print(cgc.stats())

if __name__ == "__main__":
    run()
