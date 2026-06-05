"""Native stdlib module: Rainfall Analyzer
Analyzes rainfall data by intensity, duration, and return periods.
"""
from dataclasses import dataclass, field
from typing import List, Dict
import math

@dataclass
class RainfallEvent:
    date: str
    total_mm: float
    duration_hours: float
    max_intensity_mm_hr: float

@dataclass
class RainfallAnalyzer:
    station_name: str
    events: List[RainfallEvent] = field(default_factory=list)

    def total_rainfall_mm(self) -> float:
        return sum(e.total_mm for e in self.events)

    def avg_daily_rainfall_mm(self) -> float:
        if not self.events:
            return 0.0
        return self.total_rainfall_mm() / len(self.events)

    def max_event(self) -> RainfallEvent:
        if not self.events:
            return RainfallEvent("", 0, 0, 0)
        return max(self.events, key=lambda e: e.total_mm)

    def rain_days(self, threshold_mm: float = 0.1) -> int:
        return sum(1 for e in self.events if e.total_mm >= threshold_mm)

    def intensity_distribution(self) -> Dict[str, int]:
        counts = {"light": 0, "moderate": 0, "heavy": 0, "extreme": 0}
        for e in self.events:
            if e.max_intensity_mm_hr < 2.5:
                counts["light"] += 1
            elif e.max_intensity_mm_hr < 10:
                counts["moderate"] += 1
            elif e.max_intensity_mm_hr < 50:
                counts["heavy"] += 1
            else:
                counts["extreme"] += 1
        return counts

    def stats(self) -> Dict:
        return {
            "station": self.station_name,
            "events": len(self.events),
            "total_mm": round(self.total_rainfall_mm(), 1),
            "avg_daily_mm": round(self.avg_daily_rainfall_mm(), 1),
            "max_event_mm": self.max_event().total_mm,
            "rain_days": self.rain_days(),
            "intensity_distribution": self.intensity_distribution(),
        }

def run():
    ra = RainfallAnalyzer(
        station_name="Weather Station X",
        events=[
            RainfallEvent("2024-06-01", 12.5, 4, 5.2),
            RainfallEvent("2024-06-02", 0.5, 1, 0.8),
            RainfallEvent("2024-06-03", 35.0, 2, 25.0),
            RainfallEvent("2024-06-04", 8.0, 3, 3.5),
            RainfallEvent("2024-06-05", 55.0, 3, 40.0),
        ]
    )
    print(ra.stats())

if __name__ == "__main__":
    run()
