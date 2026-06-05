"""Film Planner — shot list, schedule, budget, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class FilmPlanner:
    scenes: int = 10
    setup_time_min: float = 30.0
    shoot_time_min: float = 5.0

    def total_time(self) -> float:
        return self.scenes * (self.setup_time_min + self.shoot_time_min)

    def day_estimate(self, hours_per_day: float = 10.0) -> float:
        return self.total_time() / (hours_per_day * 60.0)

    def budget_estimate(self, crew_rate_hourly: float = 200.0, gear_daily: float = 500.0) -> float:
        days = math.ceil(self.day_estimate())
        return days * (crew_rate_hourly * 10 + gear_daily)

    def stats(self) -> Dict:
        return {"total_time_min": round(self.total_time(), 2), "days": math.ceil(self.day_estimate()), "budget_usd": round(self.budget_estimate(), 2)}

def run():
    fp = FilmPlanner(scenes=15, setup_time_min=45, shoot_time_min=8)
    print(fp.stats())

if __name__ == "__main__":
    run()
