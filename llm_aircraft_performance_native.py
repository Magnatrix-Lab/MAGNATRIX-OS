"""Aircraft Performance — climb, descent, turn, landing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class AircraftPerformance:
    weight_kg: float = 10000.0
    wing_area: float = 30.0
    max_thrust: float = 20000.0
    drag_coefficient: float = 0.02
    lift_coefficient: float = 0.5

    def wing_loading(self) -> float:
        return self.weight_kg * 9.81 / self.wing_area if self.wing_area > 0 else 0.0

    def thrust_to_weight(self) -> float:
        return self.max_thrust / (self.weight_kg * 9.81) if self.weight_kg > 0 else 0.0

    def climb_rate(self, airspeed: float = 100.0) -> float:
        excess_thrust = self.max_thrust - self.drag_coefficient * 0.5 * 1.225 * airspeed**2 * self.wing_area
        return excess_thrust / (self.weight_kg * 9.81) * airspeed if self.weight_kg > 0 else 0.0

    def turn_radius(self, bank_angle: float = 30.0, speed: float = 100.0) -> float:
        g = 9.81
        return speed**2 / (g * math.tan(math.radians(bank_angle))) if bank_angle > 0 else float('inf')

    def stall_speed(self, rho: float = 1.225) -> float:
        return math.sqrt(2 * self.weight_kg * 9.81 / (rho * self.wing_area * self.lift_coefficient)) if self.lift_coefficient > 0 else 0.0

    def landing_distance(self, approach_speed: float = 60.0, braking_decel: float = 3.0) -> float:
        return approach_speed**2 / (2 * braking_decel)

    def stats(self) -> Dict:
        return {
            "wing_loading": round(self.wing_loading(), 1),
            "thrust_weight": round(self.thrust_to_weight(), 3),
            "climb_rate": round(self.climb_rate(), 1),
            "stall_speed": round(self.stall_speed(), 1),
            "turn_radius": round(self.turn_radius(), 1)
        }

def run():
    ap = AircraftPerformance()
    print(ap.stats())
    print("Landing distance:", ap.landing_distance())

if __name__ == "__main__":
    run()
