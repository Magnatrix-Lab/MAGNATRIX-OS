"""Native stdlib module: Weight and Balance Calculator
Calculates aircraft CG, moment, and weight limits for flight planning.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Station:
    name: str
    weight_kg: float
    arm_m: float

@dataclass
class WeightBalanceCalculator:
    aircraft_empty_weight_kg: float
    aircraft_empty_cg_m: float
    max_takeoff_weight_kg: float
    max_landing_weight_kg: float
    stations: List[Station] = field(default_factory=list)

    def total_weight_kg(self) -> float:
        return self.aircraft_empty_weight_kg + sum(s.weight_kg for s in self.stations)

    def total_moment(self) -> float:
        empty_moment = self.aircraft_empty_weight_kg * self.aircraft_empty_cg_m
        return empty_moment + sum(s.weight_kg * s.arm_m for s in self.stations)

    def center_of_gravity_m(self) -> float:
        if self.total_weight_kg() == 0:
            return 0.0
        return self.total_moment() / self.total_weight_kg()

    def within_takeoff_limits(self) -> bool:
        return self.total_weight_kg() <= self.max_takeoff_weight_kg

    def within_landing_limits(self) -> bool:
        return self.total_weight_kg() <= self.max_landing_weight_kg

    def remaining_payload_kg(self) -> float:
        return max(0, self.max_takeoff_weight_kg - self.total_weight_kg())

    def stats(self) -> Dict:
        return {
            "total_weight_kg": round(self.total_weight_kg(), 1),
            "cg_m": round(self.center_of_gravity_m(), 3),
            "total_moment": round(self.total_moment(), 2),
            "within_takeoff": self.within_takeoff_limits(),
            "within_landing": self.within_landing_limits(),
            "remaining_payload_kg": round(self.remaining_payload_kg(), 1),
        }

def run():
    wbc = WeightBalanceCalculator(
        aircraft_empty_weight_kg=800,
        aircraft_empty_cg_m=2.5,
        max_takeoff_weight_kg=1600,
        max_landing_weight_kg=1500,
        stations=[
            Station("pilot", 80, 2.0),
            Station("passenger", 75, 2.0),
            Station("fuel", 200, 2.8),
            Station("baggage", 30, 3.5),
        ]
    )
    print(wbc.stats())

if __name__ == "__main__":
    run()
