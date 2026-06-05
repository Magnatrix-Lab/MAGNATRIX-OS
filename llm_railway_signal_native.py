"""Native stdlib module: Railway Signal Calculator
Calculates signal spacing, braking distances, and aspect sequences for rail signaling.
"""
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

class SignalAspect(Enum):
    RED = "red"
    YELLOW = "yellow"
    DOUBLE_YELLOW = "double_yellow"
    GREEN = "green"
    FLASHING_YELLOW = "flashing_yellow"

@dataclass
class RailwaySignalCalculator:
    max_speed_kmh: float
    deceleration_m_s2: float
    reaction_time_s: float = 3.0
    overlap_distance_m: float = 200.0

    def braking_distance_m(self) -> float:
        speed_ms = self.max_speed_kmh / 3.6
        if self.deceleration_m_s2 == 0:
            return 0.0
        return (speed_ms ** 2) / (2 * self.deceleration_m_s2)

    def reaction_distance_m(self) -> float:
        return (self.max_speed_kmh / 3.6) * self.reaction_time_s

    def total_stopping_distance_m(self) -> float:
        return self.reaction_distance_m() + self.braking_distance_m() + self.overlap_distance_m

    def signal_spacing_m(self) -> float:
        return self.total_stopping_distance_m()

    def warning_distance_m(self) -> float:
        return 2 * self.signal_spacing_m()

    def approach_locking_time_s(self) -> float:
        if self.max_speed_kmh == 0:
            return 0.0
        return (self.total_stopping_distance_m() / (self.max_speed_kmh / 3.6)) + 10

    def stats(self) -> Dict:
        return {
            "max_speed_kmh": self.max_speed_kmh,
            "braking_distance_m": round(self.braking_distance_m(), 1),
            "reaction_distance_m": round(self.reaction_distance_m(), 1),
            "total_stopping_m": round(self.total_stopping_distance_m(), 1),
            "signal_spacing_m": round(self.signal_spacing_m(), 1),
            "warning_distance_m": round(self.warning_distance_m(), 1),
            "approach_locking_s": round(self.approach_locking_time_s(), 1),
        }

def run():
    rsc = RailwaySignalCalculator(max_speed_kmh=160, deceleration_m_s2=0.8, reaction_time_s=3, overlap_distance_m=200)
    print(rsc.stats())

if __name__ == "__main__":
    run()
