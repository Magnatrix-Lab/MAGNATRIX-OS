"""Lighting Designer — lux, lumens, daylight, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class LightingDesigner:
    area_m2: float = 20.0
    ceiling_height_m: float = 2.7
    lux_target: float = 300.0

    def total_lumens(self) -> float:
        return self.area_m2 * self.lux_target

    def fixtures_needed(self, lumens_per_fixture: float = 800.0) -> int:
        return math.ceil(self.total_lumens() / lumens_per_fixture) if lumens_per_fixture > 0 else 0

    def daylight_contribution(self, window_area_m2: float = 4.0) -> float:
        return min(1.0, window_area_m2 / self.area_m2 * 3.0)

    def stats(self) -> Dict:
        return {"total_lumens": round(self.total_lumens(), 2), "fixtures": self.fixtures_needed(), "daylight_ratio": round(self.daylight_contribution(), 3)}

def run():
    ld = LightingDesigner(area_m2=40, lux_target=500)
    print(ld.stats())

if __name__ == "__main__":
    run()
