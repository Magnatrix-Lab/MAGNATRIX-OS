"""Native stdlib module: Gait Analysis Calculator
Calculates gait velocity, cadence, step length, and symmetry.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class GaitAnalysisCalculator:
    distance_m: float
    time_sec: float
    steps_count: int
    right_step_length_m: float
    left_step_length_m: float

    def velocity_m_s(self) -> float:
        if self.time_sec == 0:
            return 0.0
        return self.distance_m / self.time_sec

    def velocity_m_min(self) -> float:
        return self.velocity_m_s() * 60

    def cadence_steps_min(self) -> float:
        if self.time_sec == 0:
            return 0.0
        return (self.steps_count / self.time_sec) * 60

    def stride_length_m(self) -> float:
        return self.right_step_length_m + self.left_step_length_m

    def step_length_symmetry_pct(self) -> float:
        if self.right_step_length_m == 0:
            return 0.0
        return ((self.left_step_length_m / self.right_step_length_m) * 100) - 100

    def step_time_symmetry(self, right_step_time_sec: float, left_step_time_sec: float) -> float:
        if right_step_time_sec == 0:
            return 0.0
        return ((left_step_time_sec / right_step_time_sec) * 100) - 100

    def functional_ambulation_category(self) -> int:
        v = self.velocity_m_s()
        if v >= 1.2:
            return 5
        elif v >= 0.8:
            return 4
        elif v >= 0.4:
            return 3
        elif v >= 0.1:
            return 2
        return 1

    def stats(self) -> Dict:
        return {
            "velocity_m_s": round(self.velocity_m_s(), 2),
            "velocity_m_min": round(self.velocity_m_min(), 1),
            "cadence_steps_min": round(self.cadence_steps_min(), 1),
            "stride_length_m": round(self.stride_length_m(), 2),
            "step_length_symmetry_pct": round(self.step_length_symmetry_pct(), 1),
            "functional_ambulation": self.functional_ambulation_category(),
        }

def run():
    gac = GaitAnalysisCalculator(distance_m=10, time_sec=8.5, steps_count=12, right_step_length_m=0.72, left_step_length_m=0.68)
    print(gac.stats())

if __name__ == "__main__":
    run()
