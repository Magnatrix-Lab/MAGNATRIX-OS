"""Native stdlib module: Loom Efficiency Calculator
Calculates weaving time, picks per minute, and production efficiency.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class LoomEfficiencyCalculator:
    picks_per_inch: float
    fabric_width_in: float
    fabric_length_ft: float
    loom_speed_ppm: float = 200.0  # picks per minute
    efficiency_pct: float = 85.0

    def total_picks(self) -> float:
        return self.picks_per_inch * self.fabric_width_in * (self.fabric_length_ft * 12)

    def weaving_time_minutes(self) -> float:
        effective_ppm = self.loom_speed_ppm * (self.efficiency_pct / 100)
        if effective_ppm == 0:
            return 0
        return self.total_picks() / effective_ppm

    def weaving_time_hours(self) -> float:
        return self.weaving_time_minutes() / 60

    def production_rate_sqft_per_hour(self) -> float:
        if self.weaving_time_hours() == 0:
            return 0
        return (self.fabric_width_in * self.fabric_length_ft * 12) / (self.weaving_time_hours() * 144)

    def downtime_minutes(self) -> float:
        return self.weaving_time_minutes() * (1 - self.efficiency_pct / 100)

    def cost_at_rate(self, hourly_rate: float) -> float:
        return self.weaving_time_hours() * hourly_rate

    def daily_output_ft(self, hours_per_day: float = 8.0) -> float:
        if self.weaving_time_hours() == 0:
            return 0
        return (self.fabric_length_ft / self.weaving_time_hours()) * hours_per_day * (self.efficiency_pct / 100)

    def stats(self, hourly_rate: float = 15.0, hours_per_day: float = 8.0) -> Dict:
        return {
            "total_picks": round(self.total_picks(), 0),
            "weaving_time_hours": round(self.weaving_time_hours(), 2),
            "downtime_minutes": round(self.downtime_minutes(), 1),
            "production_rate_sqft_h": round(self.production_rate_sqft_per_hour(), 2),
            "cost_usd": round(self.cost_at_rate(hourly_rate), 2),
            "daily_output_ft": round(self.daily_output_ft(hours_per_day), 2),
            "efficiency_pct": self.efficiency_pct,
        }

def run():
    lec = LoomEfficiencyCalculator(picks_per_inch=20, fabric_width_in=30, fabric_length_ft=10, loom_speed_ppm=250, efficiency_pct=90)
    print(lec.stats())

if __name__ == "__main__":
    run()
