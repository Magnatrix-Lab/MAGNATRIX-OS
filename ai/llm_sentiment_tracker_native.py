"""LLM Sentiment Tracker — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from collections import deque

class SentimentLabel(Enum):
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()

@dataclass
class SentimentReading:
    content_id: str
    label: SentimentLabel
    score: float
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class SentimentTracker:
    def __init__(self, max_history: int = 1000) -> None:
        self._readings: deque = deque(maxlen=max_history)
        self._positive_words = {"good", "great", "excellent", "amazing", "love", "best", "happy", "wonderful", "fantastic", "awesome", "perfect", "brilliant", "outstanding", "superb", "delightful", "nice", "cool", "beautiful", "smart", "helpful", "easy", "fast", "reliable", "impressive", "enjoyable", "satisfied", "recommend", "like", "better", "improved"}
        self._negative_words = {"bad", "terrible", "awful", "worst", "hate", "horrible", "disappointing", "poor", "sad", "angry", "frustrated", "annoying", "useless", "waste", "fail", "broken", "slow", "difficult", "hard", "painful", "ugly", "stupid", "wrong", "error", "bug", "crash", "problem", "issue", "complaint", "unhappy", "dissatisfied"}

    def analyze(self, text: str, content_id: str, timestamp: str) -> SentimentReading:
        words = text.lower().split()
        pos = sum(1 for w in words if w in self._positive_words)
        neg = sum(1 for w in words if w in self._negative_words)
        total = len(words)
        if pos > neg:
            label = SentimentLabel.POSITIVE
            score = pos / total if total > 0 else 0.0
        elif neg > pos:
            label = SentimentLabel.NEGATIVE
            score = -neg / total if total > 0 else 0.0
        else:
            label = SentimentLabel.NEUTRAL
            score = 0.0
        reading = SentimentReading(content_id, label, score, timestamp)
        self._readings.append(reading)
        return reading

    def get_sentiment_trend(self, window: int = 100) -> Dict[str, Any]:
        recent = list(self._readings)[-window:]
        if not recent:
            return {"avg": 0.0, "positive_ratio": 0.0}
        scores = [r.score for r in recent]
        pos_count = sum(1 for r in recent if r.label == SentimentLabel.POSITIVE)
        return {"avg": sum(scores) / len(scores), "positive_ratio": pos_count / len(recent), "negative_ratio": sum(1 for r in recent if r.label == SentimentLabel.NEGATIVE) / len(recent), "neutral_ratio": sum(1 for r in recent if r.label == SentimentLabel.NEUTRAL) / len(recent)}

    def get_by_content(self, content_id: str) -> List[SentimentReading]:
        return [r for r in self._readings if r.content_id == content_id]

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for r in self._readings:
            counts[r.label.name] = counts.get(r.label.name, 0) + 1
        return {"readings": len(self._readings), "by_label": counts, "trend": self.get_sentiment_trend()}

def run() -> None:
    print("Sentiment Tracker test")
    e = SentimentTracker()
    e.analyze("This is amazing and wonderful!", "post_1", "2024-01-01T00:00:00")
    e.analyze("Terrible experience, very bad", "post_2", "2024-01-01T00:00:00")
    e.analyze("It was ok nothing special", "post_3", "2024-01-01T00:00:00")
    e.analyze("Great product love it", "post_4", "2024-01-01T00:00:00")
    print("  Trend: " + str(e.get_sentiment_trend()))
    print("  Stats: " + str(e.get_stats()))
    print("Sentiment Tracker test complete.")

if __name__ == "__main__":
    run()
