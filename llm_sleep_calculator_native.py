"""Native stdlib module: Sleep Calculator
Analyzes sleep quality, sleep efficiency, and circadian alignment.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class SleepEntry:
    date: str
    bedtime: str
    wake_time: str
    sleep_onset_min: float
    wake_count: int
    sleep_quality: float

@dataclass
class SleepCalculator:
    person_name: str
    entries: List[SleepEntry] = field(default_factory=list)

    def total_sleep_hours(self, entry: SleepEntry) -> float:
        from datetime import datetime
        try:
            bed = datetime.strptime(entry.bedtime, "%H:%M")
            wake = datetime.strptime(entry.wake_time, "%H:%M")
            if wake < bed:
                wake = wake.replace(day=2)
                bed = bed.replace(day=1)
            duration = (wake - bed).total_seconds() / 3600
            return max(0, duration - entry.sleep_onset_min / 60)
        except ValueError:
            return 0.0

    def avg_sleep_hours(self) -> float:
        if not self.entries:
            return 0.0
        return sum(self.total_sleep_hours(e) for e in self.entries) / len(self.entries)

    def sleep_efficiency(self, entry: SleepEntry) -> float:
        from datetime import datetime
        try:
            bed = datetime.strptime(entry.bedtime, "%H:%M")
            wake = datetime.strptime(entry.wake_time, "%H:%M")
            if wake < bed:
                wake = wake.replace(day=2)
                bed = bed.replace(day=1)
            time_in_bed = (wake - bed).total_seconds() / 3600
            if time_in_bed == 0:
                return 0.0
            return (self.total_sleep_hours(entry) / time_in_bed) * 100
        except ValueError:
            return 0.0

    def avg_efficiency(self) -> float:
        if not self.entries:
            return 0.0
        return sum(self.sleep_efficiency(e) for e in self.entries) / len(self.entries)

    def avg_quality(self) -> float:
        if not self.entries:
            return 0.0
        return sum(e.sleep_quality for e in self.entries) / len(self.entries)

    def avg_wake_count(self) -> float:
        if not self.entries:
            return 0.0
        return sum(e.wake_count for e in self.entries) / len(self.entries)

    def stats(self) -> Dict:
        return {
            "person": self.person_name,
            "entries": len(self.entries),
            "avg_sleep_hours": round(self.avg_sleep_hours(), 1),
            "avg_efficiency_pct": round(self.avg_efficiency(), 1),
            "avg_quality": round(self.avg_quality(), 1),
            "avg_wake_count": round(self.avg_wake_count(), 1),
        }

def run():
    sc = SleepCalculator(
        person_name="Jordan",
        entries=[
            SleepEntry("2024-06-01", "22:30", "06:30", 15, 1, 7),
            SleepEntry("2024-06-02", "23:00", "06:00", 20, 2, 6),
            SleepEntry("2024-06-03", "22:00", "06:00", 10, 0, 8),
            SleepEntry("2024-06-04", "22:30", "06:30", 15, 1, 7),
        ]
    )
    print(sc.stats())

if __name__ == "__main__":
    run()
