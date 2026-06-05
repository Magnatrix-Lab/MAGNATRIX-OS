"""Gear Calculator — module, teeth ratio, center distance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class GearCalculator:
    module: float = 0.2
    teeth1: int = 12
    teeth2: int = 60

    def pitch_diameter(self, teeth: int) -> float:
        return self.module * teeth

    def center_distance(self) -> float:
        return (self.pitch_diameter(self.teeth1) + self.pitch_diameter(self.teeth2)) / 2

    def gear_ratio(self) -> float:
        return self.teeth2 / self.teeth1 if self.teeth1 > 0 else 0.0

    def tooth_thickness(self) -> float:
        return math.pi * self.module / 2

    def addendum(self) -> float:
        return self.module

    def dedendum(self) -> float:
        return 1.25 * self.module

    def outer_diameter(self, teeth: int) -> float:
        return self.pitch_diameter(teeth) + 2 * self.addendum()

    def stats(self) -> Dict:
        return {"ratio": self.gear_ratio(), "center_distance": round(self.center_distance(), 3), "pd1": self.pitch_diameter(self.teeth1), "pd2": self.pitch_diameter(self.teeth2)}

def run():
    gc = GearCalculator(module=0.15, teeth1=10, teeth2=80)
    print(gc.stats())
    print("OD1:", gc.outer_diameter(gc.teeth1))

if __name__ == "__main__":
    run()
