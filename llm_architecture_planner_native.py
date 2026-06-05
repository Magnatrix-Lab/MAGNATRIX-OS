"""Architecture Planner — floor plans, spatial ratios, zoning, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class ArchitecturePlanner:
    floor_area_m2: float = 100.0
    aspect_ratio: float = 1.5
    room_count: int = 4

    def footprint(self) -> Dict:
        w = math.sqrt(self.floor_area_m2 / self.aspect_ratio)
        return {"width_m": round(w, 2), "length_m": round(w * self.aspect_ratio, 2)}

    def room_sizes(self) -> List[Dict]:
        areas = [self.floor_area_m2 / self.room_count] * self.room_count
        return [{"room_id": i+1, "area_m2": round(a, 2)} for i, a in enumerate(areas)]

    def fsi(self, plot_area_m2: float = 200.0) -> float:
        return self.floor_area_m2 / plot_area_m2 if plot_area_m2 > 0 else 0.0

    def parking_slots(self, slot_area_m2: float = 12.5) -> int:
        return int(self.floor_area_m2 / 50.0 / slot_area_m2) if slot_area_m2 > 0 else 0

    def stats(self) -> Dict:
        return {"footprint": self.footprint(), "fsi": round(self.fsi(), 3), "rooms": self.room_count}

def run():
    ap = ArchitecturePlanner(floor_area_m2=240, aspect_ratio=1.8, room_count=5)
    print(ap.stats())

if __name__ == "__main__":
    run()
