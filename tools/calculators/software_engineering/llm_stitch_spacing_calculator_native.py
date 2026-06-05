"""Native stdlib module: Stitch Spacing Calculator
Calculates SPI, thread length, needle size, and stitch spacing for leather.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import math

@dataclass
class StitchSpacingCalculator:
    stitch_length_mm: float
    seam_length_mm: float
    thread_thickness_mm: float = 0.4
    leather_thickness_mm: float = 2.0

    def stitches_per_inch(self) -> float:
        if self.stitch_length_mm == 0:
            return 0
        return 25.4 / self.stitch_length_mm

    def total_stitches(self) -> int:
        if self.stitch_length_mm == 0:
            return 0
        return int(self.seam_length_mm / self.stitch_length_mm)

    def thread_length_mm(self) -> float:
        stitches = self.total_stitches()
        return stitches * (self.stitch_length_mm * 4 + self.leather_thickness_mm * 2)

    def thread_length_m(self) -> float:
        return self.thread_length_mm() / 1000

    def needle_size_recommended(self) -> int:
        spi = self.stitches_per_inch()
        if spi < 4:
            return 1
        elif spi < 6:
            return 2
        elif spi < 8:
            return 4
        elif spi < 10:
            return 6
        return 8

    def stitch_visibility(self) -> str:
        spi = self.stitches_per_inch()
        if spi < 4:
            return "bold"
        elif spi < 7:
            return "standard"
        elif spi < 10:
            return "fine"
        return "very_fine"

    def stats(self) -> Dict:
        return {
            "stitch_length_mm": self.stitch_length_mm,
            "seam_length_mm": self.seam_length_mm,
            "stitches_per_inch": round(self.stitches_per_inch(), 1),
            "total_stitches": self.total_stitches(),
            "thread_length_mm": round(self.thread_length_mm(), 1),
            "thread_length_m": round(self.thread_length_m(), 2),
            "needle_size": self.needle_size_recommended(),
            "stitch_visibility": self.stitch_visibility(),
        }

def run():
    ssc = StitchSpacingCalculator(stitch_length_mm=4, seam_length_mm=200, leather_thickness_mm=3)
    print(ssc.stats())

if __name__ == "__main__":
    run()
