"""Aircraft Performance — climb, descent, range, endurance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class AircraftPerformance:
    weight: float = 70000.0
    wing_area: float = 122.0
    max_thrust: float = 120000.0
    fuel_capacity: float = 20000.0
    sfc: float = 0.5

    def wing_loading(self) -> float:
        return self.weight / self.wing_area if self.wing_area > 0 else 0.0

    def thrust_to_weight(self) -> float:
        return self.max_thrust / self.weight if self.weight > 0 else 0.0

    def climb_rate(self, excess_thrust: float) -> float:
        return excess_thrust / self.weight * 60 if self.weight > 0 else 0.0

    def range_breguet(self, l_d: float = 15.0, v: float = 250.0) -> float:
        if self.sfc <= 0 or l_d <= 0:
            return 0.0
        return v / self.sfc * l_d * math.log(self.weight / (self.weight - self.fuel_capacity))

    def endurance(self, l_d: float = 15.0) -> float:
        if self.sfc <= 0 or l_d <= 0:
            return 0.0
        return l_d / self.sfc * math.log(self.weight / (self.weight - self.fuel_capacity))

    def descent_rate(self, glide_ratio: float = 10.0) -> float:
        return self.weight / glide_ratio if glide_ratio > 0 else 0.0

    def stats(self) -> Dict:
        return {"wing_loading": round(self.wing_loading(), 1), "t_w": round(self.thrust_to_weight(), 3), "range": round(self.range_breguet(), 0)}

def run():
    ap = AircraftPerformance()
    print(ap.stats())
    print("Endurance:", ap.endurance())
    print("Climb rate:", ap.climb_rate(50000))

if __name__ == "__main__":
    run()
