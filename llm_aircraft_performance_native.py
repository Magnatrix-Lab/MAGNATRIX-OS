"""Aircraft Performance — takeoff, landing, climb, ceiling, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class AircraftPerformance:
    weight_kg: float = 50000.0
    wing_area: float = 122.0
    max_thrust: float = 120000.0
    cd0: float = 0.02
    cl_max: float = 2.0

    def wing_loading(self) -> float:
        return self.weight_kg * 9.81 / self.wing_area

    def thrust_to_weight(self) -> float:
        return self.max_thrust / (self.weight_kg * 9.81)

    def stall_speed(self, rho: float = 1.225) -> float:
        return math.sqrt(2 * self.weight_kg * 9.81 / (rho * self.wing_area * self.cl_max))

    def takeoff_distance(self, mu: float = 0.03) -> float:
        a = (self.max_thrust - mu * self.weight_kg * 9.81) / self.weight_kg
        v_stall = self.stall_speed()
        return 1.2 * v_stall ** 2 / (2 * a)

    def climb_rate(self, rho: float = 1.225) -> float:
        v = self.stall_speed() * 1.5
        drag = 0.5 * rho * v**2 * self.wing_area * self.cd0
        excess = self.max_thrust - drag
        return excess * v / (self.weight_kg * 9.81)

    def service_ceiling(self) -> float:
        return 10000 + self.climb_rate() * 30

    def stats(self) -> Dict:
        return {"wing_loading": round(self.wing_loading(), 1), "thrust_weight": round(self.thrust_to_weight(), 3), "stall_speed": round(self.stall_speed(), 1), "takeoff_m": round(self.takeoff_distance(), 0)}

def run():
    ap = AircraftPerformance()
    print(ap.stats())
    print("Climb rate:", round(ap.climb_rate(), 1), "m/s")

if __name__ == "__main__":
    run()
