"""Native stdlib module: Plate Tectonics Calculator
Calculates plate motion, spreading rates, and convergence velocities.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class PlateTectonicsCalculator:
    plate_a_name: str
    plate_b_name: str
    relative_velocity_mm_per_year: float
    boundary_type: str = "divergent"
    distance_km: float = 1000

    def spreading_rate_cm_per_year(self) -> float:
        if self.boundary_type == "divergent":
            return self.relative_velocity_mm_per_year / 10
        return 0.0

    def convergence_rate_cm_per_year(self) -> float:
        if self.boundary_type == "convergent":
            return self.relative_velocity_mm_per_year / 10
        return 0.0

    def time_to_close_gap_million_years(self) -> float:
        if self.relative_velocity_mm_per_year == 0:
            return 0.0
        return (self.distance_km * 1_000_000) / (self.relative_velocity_mm_per_year * 1_000_000)

    def subduction_rate_cm_per_year(self) -> float:
        if self.boundary_type == "convergent":
            return self.relative_velocity_mm_per_year / 10
        return 0.0

    def transform_slip_rate_cm_per_year(self) -> float:
        if self.boundary_type == "transform":
            return self.relative_velocity_mm_per_year / 10
        return 0.0

    def stats(self) -> Dict:
        return {
            "plate_a": self.plate_a_name,
            "plate_b": self.plate_b_name,
            "boundary_type": self.boundary_type,
            "relative_velocity_mm_yr": self.relative_velocity_mm_per_year,
            "spreading_cm_yr": round(self.spreading_rate_cm_per_year(), 2),
            "convergence_cm_yr": round(self.convergence_rate_cm_per_year(), 2),
            "time_to_close_gap_my": round(self.time_to_close_gap_million_years(), 2),
        }

def run():
    ptc = PlateTectonicsCalculator(plate_a_name="Eurasian", plate_b_name="North American", relative_velocity_mm_per_year=25, boundary_type="divergent", distance_km=500)
    print(ptc.stats())

if __name__ == "__main__":
    run()
