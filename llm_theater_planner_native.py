"""Theater Planner — seating, sightlines, acoustics, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class TheaterPlanner:
    seats: int = 200
    stage_width_m: float = 12.0
    stage_depth_m: float = 8.0

    def seat_area(self, area_per_seat_m2: float = 0.55) -> float:
        return self.seats * area_per_seat_m2

    def sightline_check(self, seat_row: int, seat_height_m: float = 0.9, riser_m: float = 0.3) -> bool:
        eye_level = seat_height_m + riser_m * seat_row
        stage_height = 1.0
        return eye_level > stage_height

    def stage_volume_m3(self, height_m: float = 6.0) -> float:
        return self.stage_width_m * self.stage_depth_m * height_m

    def stats(self) -> Dict:
        return {"seat_area_m2": round(self.seat_area(), 2), "stage_volume_m3": round(self.stage_volume_m3(), 2), "sightline_ok": self.sightline_check(5)}

def run():
    tp = TheaterPlanner(seats=350, stage_width_m=15, stage_depth_m=10)
    print(tp.stats())

if __name__ == "__main__":
    run()
