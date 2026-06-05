"""Native stdlib module: Annealing Schedule Calculator
Calculates annealing schedules, strain points, and soak times.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class AnnealingScheduleCalculator:
    strain_point_c: float
    thickness_mm: float
    coe: float = 96.0

    def annealing_point_c(self) -> float:
        return self.strain_point_c + 40

    def softening_point_c(self) -> float:
        return self.strain_point_c + 200

    def soak_time_min(self) -> float:
        return max(30, self.thickness_mm * 15)

    def initial_cool_rate_c_per_hour(self) -> float:
        return max(5, 100 / (self.thickness_mm ** 0.5))

    def total_annealing_time_hours(self) -> float:
        soak = self.soak_time_min() / 60
        cool_down = (self.annealing_point_c() - 400) / self.initial_cool_rate_c_per_hour()
        return soak + cool_down

    def schedule_phases(self) -> Dict:
        return {
            "heat_to_softening": self.softening_point_c(),
            "soak_at_annealing": self.annealing_point_c(),
            "soak_time_min": round(self.soak_time_min(), 0),
            "cool_to_strain": self.strain_point_c(),
            "cool_rate_initial": round(self.initial_cool_rate_c_per_hour(), 1),
        }

    def stats(self) -> Dict:
        return {
            "strain_point_c": self.strain_point_c,
            "annealing_point_c": self.annealing_point_c(),
            "softening_point_c": self.softening_point_c(),
            "soak_time_min": round(self.soak_time_min(), 0),
            "cool_rate_c_per_hour": round(self.initial_cool_rate_c_per_hour(), 1),
            "total_annealing_time_hours": round(self.total_annealing_time_hours(), 1),
        }

def run():
    asc = AnnealingScheduleCalculator(strain_point_c=510, thickness_mm=6, coe=96)
    print(asc.stats())
    print(asc.schedule_phases())

if __name__ == "__main__":
    run()
