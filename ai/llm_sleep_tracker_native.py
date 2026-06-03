"""LLM Sleep Tracker — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime

class SleepQuality(Enum):
    EXCELLENT = auto()
    GOOD = auto()
    FAIR = auto()
    POOR = auto()
    TERRIBLE = auto()

@dataclass
class SleepEntry:
    id: str
    start_time: str
    end_time: str
    quality: SleepQuality
    interruptions: int = 0
    deep_sleep_min: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class SleepTracker:
    def __init__(self) -> None:
        self._entries: List[SleepEntry] = []

    def add_entry(self, entry: SleepEntry) -> None:
        self._entries.append(entry)

    def get_duration(self, entry: SleepEntry) -> float:
        try:
            start = datetime.fromisoformat(entry.start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(entry.end_time.replace("Z", "+00:00"))
            return (end - start).total_seconds() / 3600
        except Exception:
            return 0.0

    def get_average_duration(self, last_n: int = 7) -> float:
        recent = self._entries[-last_n:]
        if not recent:
            return 0.0
        durations = [self.get_duration(e) for e in recent]
        return sum(durations) / len(durations)

    def get_quality_score(self, entry: SleepEntry) -> float:
        duration = self.get_duration(entry)
        base_score = {"EXCELLENT": 10, "GOOD": 8, "FAIR": 6, "POOR": 4, "TERRIBLE": 2}[entry.quality.name]
        duration_bonus = min(2, max(-2, (duration - 7.5) * 0.5))
        interruption_penalty = entry.interruptions * 0.5
        return max(0, base_score + duration_bonus - interruption_penalty)

    def get_sleep_debt(self, target_hours: float = 8.0) -> float:
        if not self._entries:
            return 0.0
        total = sum(self.get_duration(e) for e in self._entries)
        expected = target_hours * len(self._entries)
        return max(0, expected - total)

    def get_stats(self) -> Dict[str, Any]:
        if not self._entries:
            return {}
        durations = [self.get_duration(e) for e in self._entries]
        qualities = {}
        for e in self._entries:
            qualities[e.quality.name] = qualities.get(e.quality.name, 0) + 1
        return {"entries": len(self._entries), "avg_duration": sum(durations) / len(durations), "sleep_debt": self.get_sleep_debt(), "by_quality": qualities}

def run() -> None:
    print("Sleep Tracker test")
    e = SleepTracker()
    e.add_entry(SleepEntry("s1", "2024-01-01T22:00:00", "2024-01-02T06:00:00", SleepQuality.GOOD, 1, 180))
    e.add_entry(SleepEntry("s2", "2024-01-02T23:00:00", "2024-01-03T06:30:00", SleepQuality.FAIR, 2, 120))
    e.add_entry(SleepEntry("s3", "2024-01-03T21:30:00", "2024-01-04T07:00:00", SleepQuality.EXCELLENT, 0, 240))
    print("  Avg duration: " + str(e.get_average_duration()))
    print("  Sleep debt: " + str(e.get_sleep_debt()))
    print("  Quality score: " + str(e.get_quality_score(e._entries[0])))
    print("  Stats: " + str(e.get_stats()))
    print("Sleep Tracker test complete.")

if __name__ == "__main__":
    run()
