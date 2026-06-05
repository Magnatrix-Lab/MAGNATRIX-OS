"""Tailings Dam — storage, embankment, seepage, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class TailingsDam:
    area_m2: float = 100000.0
    dam_height: float = 20.0
    slope_ratio: float = 2.5
    tailings_density: float = 1.8

    def storage_volume(self) -> float:
        return self.area_m2 * self.dam_height

    def embankment_volume(self) -> float:
        base_width = self.dam_height * self.slope_ratio * 2
        return 0.5 * base_width * self.dam_height * 100

    def seepage_rate(self, permeability: float = 1e-7, hydraulic_gradient: float = 0.1) -> float:
        return permeability * hydraulic_gradient * self.area_m2

    def freeboard_required(self, design_flood: float = 1.0) -> float:
        return 1.5 + design_flood * 0.5

    def stability_check(self, fos_required: float = 1.5) -> bool:
        return self.slope_ratio >= 2.0 and self.dam_height < 50

    def stats(self) -> Dict:
        return {"storage_m3": round(self.storage_volume(), 0), "embankment_m3": round(self.embankment_volume(), 0), "stable": self.stability_check()}

def run():
    td = TailingsDam(area_m2=500000, dam_height=35, slope_ratio=3.0)
    print(td.stats())

if __name__ == "__main__":
    run()
