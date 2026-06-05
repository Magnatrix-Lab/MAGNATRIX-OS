"""Color Grader — lift/gamma/gain, color temp, saturation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class ColorGrader:
    lift: float = 0.0
    gamma: float = 1.0
    gain: float = 1.0
    saturation: float = 1.0

    def grade_value(self, input_value: float = 0.5) -> float:
        v = (input_value + self.lift) * self.gain
        return v ** (1.0 / self.gamma) if self.gamma > 0 else v

    def kelvin_shift(self, from_k: float = 5600.0, to_k: float = 3200.0) -> Dict:
        ratio = to_k / from_k if from_k > 0 else 1.0
        return {"red_mult": round(min(1.5, ratio), 3), "blue_mult": round(min(1.5, 1.0 / ratio), 3)}

    def contrast_curve(self, x: float = 0.5, pivot: float = 0.5) -> float:
        return (x - pivot) * self.gain + pivot + self.lift

    def stats(self) -> Dict:
        return {"graded_mid": round(self.grade_value(), 3), "kelvin_shift": self.kelvin_shift(), "contrast_pivot": round(self.contrast_curve(), 3)}

def run():
    cg = ColorGrader(lift=0.05, gamma=1.2, gain=1.1, saturation=1.15)
    print(cg.stats())

if __name__ == "__main__":
    run()
