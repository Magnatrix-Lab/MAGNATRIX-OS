"""Native stdlib module: Aging Tracker
Tracks cheese aging by humidity, temperature, flip schedule, and weight loss.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime, timedelta

@dataclass
class AgingReading:
    day: int
    temp_c: float
    humidity_pct: float
    weight_g: float

@dataclass
class AgingTracker:
    cheese_name: str
    start_weight_g: float
    start_date: str
    target_days: int
    target_humidity_pct: float = 85.0
    target_temp_c: float = 12.0
    readings: List[AgingReading] = field(default_factory=list)

    def weight_loss_pct(self) -> float:
        if not self.readings:
            return 0.0
        latest = self.readings[-1].weight_g
        return ((self.start_weight_g - latest) / self.start_weight_g) * 100

    def days_elapsed(self) -> int:
        return len(self.readings)

    def avg_temp(self) -> float:
        if not self.readings:
            return 0.0
        return sum(r.temp_c for r in self.readings) / len(self.readings)

    def stats(self) -> Dict:
        return {
            "days_elapsed": self.days_elapsed(),
            "weight_loss_pct": round(self.weight_loss_pct(), 2),
            "avg_temp_c": round(self.avg_temp(), 1),
            "target_days": self.target_days,
        }

def run():
    at = AgingTracker(
        cheese_name="Gouda", start_weight_g=2500, start_date="2024-01-01", target_days=60,
        readings=[
            AgingReading(1, 12, 85, 2480),
            AgingReading(7, 12, 84, 2420),
            AgingReading(14, 13, 83, 2350),
        ]
    )
    print(at.stats())

if __name__ == "__main__":
    run()
