"""Native stdlib module: Ceramic Firing Calculator
Calculates firing schedules, shrinkage, and glaze fit for ceramics.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class FiringSegment:
    segment_name: str
    start_temp_c: float
    end_temp_c: float
    rate_c_per_hour: float
    hold_time_hours: float

@dataclass
class CeramicFiringCalculator:
    kiln_name: str
    max_temp_c: float
    segments: List[FiringSegment] = field(default_factory=list)
    greenware_shrinkage_pct: float = 8.0
    glaze_thickness_mm: float = 0.5

    def total_firing_time_hours(self) -> float:
        firing_time = 0.0
        for seg in self.segments:
            if seg.rate_c_per_hour > 0:
                firing_time += abs(seg.end_temp_c - seg.start_temp_c) / seg.rate_c_per_hour
            firing_time += seg.hold_time_hours
        return firing_time

    def total_heat_work(self) -> float:
        return sum(seg.end_temp_c * (seg.hold_time_hours + 1) for seg in self.segments)

    def cone_equivalent(self) -> str:
        if self.max_temp_c < 1000:
            return "04-06"
        elif self.max_temp_c < 1200:
            return "03-1"
        elif self.max_temp_c < 1260:
            return "2-5"
        elif self.max_temp_c < 1300:
            return "6-8"
        elif self.max_temp_c < 1350:
            return "9-10"
        return "11-12"

    def firing_cost_estimate(self, energy_cost_kwh: float = 0.15, kiln_power_kw: float = 50) -> float:
        return self.total_firing_time_hours() * kiln_power_kw * energy_cost_kwh

    def final_dimension_mm(self, original_mm: float) -> float:
        return original_mm * (1 - self.greenware_shrinkage_pct / 100)

    def stats(self) -> Dict:
        return {
            "kiln": self.kiln_name,
            "max_temp_c": self.max_temp_c,
            "cone": self.cone_equivalent(),
            "total_firing_time_hr": round(self.total_firing_time_hours(), 1),
            "total_heat_work": round(self.total_heat_work(), 1),
            "firing_cost_usd": round(self.firing_cost_estimate(), 2),
            "segments": len(self.segments),
        }

def run():
    cfc = CeramicFiringCalculator(
        kiln_name="Gas Kiln 1",
        max_temp_c=1240,
        segments=[
            FiringSegment("Preheat", 20, 120, 100, 0),
            FiringSegment("Water smoking", 120, 300, 150, 0),
            FiringSegment("Oxidation", 300, 900, 200, 0),
            FiringSegment("Reduction", 900, 1240, 150, 0.5),
            FiringSegment("Cooling", 1240, 200, 100, 0),
        ],
        greenware_shrinkage_pct=10
    )
    print(cfc.stats())

if __name__ == "__main__":
    run()
