"""Native stdlib module: Rail Capacity Calculator
Calculates line capacity, train frequency, and throughput for rail networks.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class RailCapacityCalculator:
    line_name: str
    block_length_km: float
    max_speed_kmh: float
    train_length_m: float
    braking_distance_m: float
    dwell_time_min: float = 2.0

    def headway_min(self) -> float:
        if self.max_speed_kmh == 0:
            return 0.0
        travel_time_min = (self.block_length_km / self.max_speed_kmh) * 60
        return travel_time_min + self.dwell_time_min + (self.braking_distance_m / 1000 / self.max_speed_kmh * 60)

    def trains_per_hour(self) -> float:
        if self.headway_min() == 0:
            return 0.0
        return 60 / self.headway_min()

    def daily_capacity_trains(self, operating_hours: float = 18) -> int:
        return int(self.trains_per_hour() * operating_hours)

    def platform_occupancy_pct(self, platform_length_m: float) -> float:
        if platform_length_m == 0:
            return 0.0
        return (self.train_length_m / platform_length_m) * 100

    def stats(self) -> Dict:
        return {
            "line": self.line_name,
            "headway_min": round(self.headway_min(), 1),
            "trains_per_hour": round(self.trains_per_hour(), 1),
            "daily_capacity": self.daily_capacity_trains(),
            "platform_occupancy_pct": round(self.platform_occupancy_pct(), 1),
        }

def run():
    rc = RailCapacityCalculator(line_name="Metro Line A", block_length_km=2, max_speed_kmh=80, train_length_m=120, braking_distance_m=200, dwell_time_min=1.5)
    print(rc.stats())

if __name__ == "__main__":
    run()
