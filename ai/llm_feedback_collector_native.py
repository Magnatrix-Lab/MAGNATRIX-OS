"""
llm_feedback_collector_native.py
MAGNATRIX-OS Feedback Collector Engine
Native Python, stdlib only.
Provides feedback collection, rating aggregation, sentiment analysis, and improvement tracking.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class FeedbackType(Enum):
    RATING = "rating"
    THUMBS = "thumbs"
    TEXT = "text"
    MULTI_SELECT = "multi_select"
    NPS = "nps"


class FeedbackSentiment(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class FeedbackEntry:
    entry_id: str
    user_id: str
    feedback_type: FeedbackType
    value: Any
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id, "user_id": self.user_id,
            "type": self.feedback_type.value, "value": self.value,
            "timestamp": self.timestamp, "tags": self.tags,
        }


class FeedbackCollectorEngine:
    """Feedback collection with aggregation and sentiment analysis."""

    def __init__(self) -> None:
        self._entries: List[FeedbackEntry] = []
        self._handlers: List[Callable[[FeedbackEntry], None]] = []
        self._counter = 0

    def collect(self, user_id: str, feedback_type: FeedbackType, value: Any,
                context: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None) -> FeedbackEntry:
        self._counter += 1
        entry = FeedbackEntry(
            entry_id=f"fb_{int(time.time() * 1000)}_{self._counter}",
            user_id=user_id, feedback_type=feedback_type, value=value,
            context=context or {}, tags=tags or []
        )
        self._entries.append(entry)
        for handler in self._handlers:
            try:
                handler(entry)
            except Exception:
                pass
        return entry

    def add_handler(self, handler: Callable[[FeedbackEntry], None]) -> None:
        self._handlers.append(handler)

    def get_average_rating(self, feedback_type: Optional[FeedbackType] = None) -> float:
        entries = self._entries
        if feedback_type:
            entries = [e for e in entries if e.feedback_type == feedback_type]
        ratings = [e.value for e in entries if isinstance(e.value, (int, float))]
        return sum(ratings) / len(ratings) if ratings else 0.0

    def get_nps(self) -> Optional[float]:
        nps_entries = [e.value for e in self._entries if e.feedback_type == FeedbackType.NPS and isinstance(e.value, int)]
        if not nps_entries:
            return None
        promoters = sum(1 for v in nps_entries if v >= 9)
        detractors = sum(1 for v in nps_entries if v <= 6)
        return ((promoters - detractors) / len(nps_entries)) * 100

    def get_sentiment_distribution(self) -> Dict[str, int]:
        dist = {"positive": 0, "neutral": 0, "negative": 0}
        for e in self._entries:
            if e.feedback_type == FeedbackType.THUMBS:
                if e.value == "up":
                    dist["positive"] += 1
                elif e.value == "down":
                    dist["negative"] += 1
            elif e.feedback_type == FeedbackType.RATING and isinstance(e.value, (int, float)):
                if e.value >= 4:
                    dist["positive"] += 1
                elif e.value >= 3:
                    dist["neutral"] += 1
                else:
                    dist["negative"] += 1
        return dist

    def get_by_tag(self, tag: str) -> List[FeedbackEntry]:
        return [e for e in self._entries if tag in e.tags]

    def get_trend(self, window_seconds: float = 3600) -> Dict[str, float]:
        now = time.time()
        recent = [e for e in self._entries if e.timestamp >= now - window_seconds]
        ratings = [e.value for e in recent if isinstance(e.value, (int, float))]
        return {
            "count": len(recent), "avg_rating": sum(ratings) / len(ratings) if ratings else 0.0,
        }

    def get_stats(self) -> Dict[str, Any]:
        by_type: Dict[str, int] = {}
        for e in self._entries:
            by_type[e.feedback_type.value] = by_type.get(e.feedback_type.value, 0) + 1
        return {
            "total_entries": len(self._entries), "by_type": by_type,
            "avg_rating": self.get_average_rating(), "nps": self.get_nps(),
            "sentiment": self.get_sentiment_distribution(),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._entries], f, indent=2, default=str)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Feedback Collector Engine")
    print("=" * 60)

    engine = FeedbackCollectorEngine()

    def feedback_handler(entry: FeedbackEntry) -> None:
        if entry.feedback_type == FeedbackType.RATING and entry.value <= 2:
            print(f"  [LOW RATING] {entry.user_id}: {entry.value}")

    engine.add_handler(feedback_handler)

    print("\n--- Collect feedback ---")
    for i in range(10):
        engine.collect(f"user_{i}", FeedbackType.RATING, 5 if i < 7 else 2, tags=["production"])

    for i in range(5):
        engine.collect(f"user_{i}", FeedbackType.NPS, 10 if i < 3 else 5, tags=["nps_survey"])

    engine.collect("user_a", FeedbackType.THUMBS, "up", tags=["ui"])
    engine.collect("user_b", FeedbackType.THUMBS, "down", tags=["ui"])

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\n--- NPS ---")
    print(f"  NPS Score: {engine.get_nps()}")

    print("\n--- Sentiment ---")
    print(f"  {engine.get_sentiment_distribution()}")

    print("\nFeedback Collector test complete.")


if __name__ == "__main__":
    run()
