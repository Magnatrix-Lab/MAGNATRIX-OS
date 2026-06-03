"""LLM Feedback Collector — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class FeedbackType(Enum):
    THUMB_UP = auto()
    THUMB_DOWN = auto()
    RATING = auto()
    COMMENT = auto()
    FLAG = auto()

@dataclass
class FeedbackEntry:
    id: str
    feedback_type: FeedbackType
    value: Any
    user_id: str
    target_id: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class FeedbackCollector:
    def __init__(self) -> None:
        self._entries: List[FeedbackEntry] = []
        self._index: Dict[str, List[int]] = {}

    def add(self, entry: FeedbackEntry) -> None:
        idx = len(self._entries)
        self._entries.append(entry)
        if entry.target_id not in self._index:
            self._index[entry.target_id] = []
        self._index[entry.target_id].append(idx)

    def get_for_target(self, target_id: str) -> List[FeedbackEntry]:
        indices = self._index.get(target_id, [])
        return [self._entries[i] for i in indices]

    def get_rating_average(self, target_id: str) -> float:
        entries = [e for e in self.get_for_target(target_id) if e.feedback_type == FeedbackType.RATING]
        if not entries:
            return 0.0
        return sum(e.value for e in entries) / len(entries)

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for e in self._entries:
            counts[e.feedback_type.name] = counts.get(e.feedback_type.name, 0) + 1
        return {"total": len(self._entries), "by_type": counts, "targets": len(self._index)}

def run() -> None:
    print("Feedback Collector test")
    e = FeedbackCollector()
    e.add(FeedbackEntry("f1", FeedbackType.RATING, 4.5, "user1", "output_1", "2024-01-01T10:00:00"))
    e.add(FeedbackEntry("f2", FeedbackType.THUMB_UP, True, "user2", "output_1", "2024-01-01T10:01:00"))
    e.add(FeedbackEntry("f3", FeedbackType.COMMENT, "Very helpful", "user3", "output_2", "2024-01-01T10:02:00"))
    print("  For output_1: " + str(len(e.get_for_target("output_1"))) + " entries")
    print("  Rating avg output_1: " + str(e.get_rating_average("output_1")))
    print("  Stats: " + str(e.get_stats()))
    print("Feedback Collector test complete.")

if __name__ == "__main__":
    run()
