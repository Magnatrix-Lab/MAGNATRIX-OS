"""Furniture Optimizer — layout, clearance, scale, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class FurnitureOptimizer:
    room_width_m: float = 4.0
    room_length_m: float = 5.0
    furniture: List[Dict] = field(default_factory=list)

    def total_furniture_area(self) -> float:
        return sum(f.get("width", 0) * f.get("depth", 0) for f in self.furniture)

    def clearance_ok(self, min_clearance_m: float = 0.6) -> bool:
        room_perimeter = 2 * (self.room_width_m + self.room_length_m)
        used = sum(2 * (f.get("width", 0) + f.get("depth", 0)) for f in self.furniture)
        return (room_perimeter - used) >= min_clearance_m * len(self.furniture)

    def open_space_ratio(self) -> float:
        room = self.room_width_m * self.room_length_m
        return 1 - (self.total_furniture_area() / room) if room > 0 else 0.0

    def stats(self) -> Dict:
        return {"furniture_area_m2": round(self.total_furniture_area(), 2), "clearance_ok": self.clearance_ok(), "open_ratio": round(self.open_space_ratio(), 3)}

def run():
    fo = FurnitureOptimizer(room_width_m=5, room_length_m=6, furniture=[{"width": 2, "depth": 1}, {"width": 1, "depth": 0.8}])
    print(fo.stats())

if __name__ == "__main__":
    run()
