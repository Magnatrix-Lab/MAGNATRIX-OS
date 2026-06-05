"""Interior Designer — color schemes, material palettes, mood board, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class InteriorDesigner:
    room_area_m2: float = 20.0
    style: str = "modern"

    def paint_needed(self, coats: int = 2, coverage_per_l: float = 10.0) -> float:
        return (self.room_area_m2 * coats) / coverage_per_l if coverage_per_l > 0 else 0.0

    def flooring_cost(self, material_cost_per_m2: float = 25.0) -> float:
        return self.room_area_m2 * material_cost_per_m2

    def lighting_lumens(self, lux_required: float = 300.0) -> float:
        return self.room_area_m2 * lux_required

    def stats(self) -> Dict:
        return {"paint_liters": round(self.paint_needed(), 2), "flooring_usd": round(self.flooring_cost(), 2), "lumens": round(self.lighting_lumens(), 2)}

def run():
    id = InteriorDesigner(room_area_m2=35, style="scandinavian")
    print(id.stats())

if __name__ == "__main__":
    run()
