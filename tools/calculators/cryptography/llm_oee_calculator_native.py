"""Native stdlib module: OEE Calculator
Calculates Overall Equipment Effectiveness from availability, performance, and quality.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class OEECalculator:
    machine_name: str
    planned_production_time_min: float
    downtime_min: float
    ideal_cycle_time_sec: float
    total_count: int
    good_count: int

    def availability(self) -> float:
        if self.planned_production_time_min == 0:
            return 0.0
        run_time = self.planned_production_time_min - self.downtime_min
        return run_time / self.planned_production_time_min

    def performance(self) -> float:
        run_time_sec = (self.planned_production_time_min - self.downtime_min) * 60
        if run_time_sec == 0:
            return 0.0
        return (self.total_count * self.ideal_cycle_time_sec) / run_time_sec

    def quality(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.good_count / self.total_count

    def oee(self) -> float:
        return self.availability() * self.performance() * self.quality()

    def oee_pct(self) -> float:
        return self.oee() * 100

    def stats(self) -> Dict[str, float]:
        return {
            "availability_pct": round(self.availability() * 100, 1),
            "performance_pct": round(self.performance() * 100, 1),
            "quality_pct": round(self.quality() * 100, 1),
            "oee_pct": round(self.oee_pct(), 1),
        }

def run():
    oee = OEECalculator(
        machine_name="Press-01",
        planned_production_time_min=480,
        downtime_min=45,
        ideal_cycle_time_sec=30,
        total_count=800,
        good_count=760
    )
    print(oee.stats())

if __name__ == "__main__":
    run()
