"""Native stdlib module: Mood Tracker
Tracks mood scores, patterns, and trends over time.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime

@dataclass
class MoodEntry:
    date: str
    mood_score: float
    anxiety_score: float
    sleep_hours: float
    notes: str = ""

@dataclass
class MoodTracker:
    person_name: str
    entries: List[MoodEntry] = field(default_factory=list)

    def avg_mood(self) -> float:
        if not self.entries:
            return 0.0
        return sum(e.mood_score for e in self.entries) / len(self.entries)

    def avg_anxiety(self) -> float:
        if not self.entries:
            return 0.0
        return sum(e.anxiety_score for e in self.entries) / len(self.entries)

    def avg_sleep(self) -> float:
        if not self.entries:
            return 0.0
        return sum(e.sleep_hours for e in self.entries) / len(self.entries)

    def mood_trend(self) -> str:
        if len(self.entries) < 2:
            return "stable"
        first_half = sum(e.mood_score for e in self.entries[:len(self.entries)//2]) / max(1, len(self.entries)//2)
        second_half = sum(e.mood_score for e in self.entries[len(self.entries)//2:]) / max(1, len(self.entries) - len(self.entries)//2)
        if second_half > first_half + 0.5:
            return "improving"
        elif second_half < first_half - 0.5:
            return "declining"
        return "stable"

    def low_mood_days(self, threshold: float = 3.0) -> int:
        return sum(1 for e in self.entries if e.mood_score <= threshold)

    def stats(self) -> Dict:
        return {
            "person": self.person_name,
            "entries": len(self.entries),
            "avg_mood": round(self.avg_mood(), 1),
            "avg_anxiety": round(self.avg_anxiety(), 1),
            "avg_sleep": round(self.avg_sleep(), 1),
            "trend": self.mood_trend(),
            "low_mood_days": self.low_mood_days(),
        }

def run():
    mt = MoodTracker(
        person_name="Sam",
        entries=[
            MoodEntry("2024-06-01", 6, 4, 7.5),
            MoodEntry("2024-06-02", 5, 5, 6.0),
            MoodEntry("2024-06-03", 7, 3, 8.0),
            MoodEntry("2024-06-04", 6, 4, 7.0),
            MoodEntry("2024-06-05", 8, 2, 8.5),
        ]
    )
    print(mt.stats())

if __name__ == "__main__":
    run()
