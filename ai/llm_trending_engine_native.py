"""LLM Trending Engine — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime, timedelta

@dataclass
class TrendItem:
    term: str
    score: float
    velocity: float
    volume: int
    timestamp: str

class TrendingEngine:
    def __init__(self, decay_factor: float = 0.95) -> None:
        self._scores: Dict[str, float] = {}
        self._counts: Dict[str, int] = {}
        self._timestamps: Dict[str, str] = {}
        self._decay_factor = decay_factor
        self._history: Dict[str, List[tuple]] = {}

    def add_occurrence(self, term: str, timestamp: str, weight: float = 1.0) -> None:
        term = term.lower()
        self._scores[term] = self._scores.get(term, 0) * self._decay_factor + weight
        self._counts[term] = self._counts.get(term, 0) + 1
        self._timestamps[term] = timestamp
        if term not in self._history:
            self._history[term] = []
        self._history[term].append((timestamp, weight))

    def get_trending(self, n: int = 10) -> List[TrendItem]:
        items = []
        for term in self._scores:
            score = self._scores[term]
            velocity = self._calculate_velocity(term)
            items.append(TrendItem(term, score, velocity, self._counts[term], self._timestamps.get(term, "")))
        items.sort(key=lambda x: x.score, reverse=True)
        return items[:n]

    def _calculate_velocity(self, term: str) -> float:
        history = self._history.get(term, [])
        if len(history) < 2:
            return 0.0
        recent = history[-10:]
        if len(recent) < 2:
            return 0.0
        weights = [w for _, w in recent]
        return (weights[-1] - weights[0]) / len(weights) if weights else 0.0

    def get_emerging(self, n: int = 5) -> List[TrendItem]:
        items = []
        for term in self._scores:
            velocity = self._calculate_velocity(term)
            if velocity > 0:
                items.append(TrendItem(term, self._scores[term], velocity, self._counts[term], self._timestamps.get(term, "")))
        items.sort(key=lambda x: x.velocity, reverse=True)
        return items[:n]

    def get_stats(self) -> Dict[str, Any]:
        return {"tracked": len(self._scores), "total_occurrences": sum(self._counts.values()), "trending": len(self.get_trending())}

def run() -> None:
    print("Trending Engine test")
    e = TrendingEngine()
    for i in range(20):
        e.add_occurrence("AI", "2024-01-01T00:00:00", 1.0 + i * 0.1)
    for i in range(10):
        e.add_occurrence("Python", "2024-01-01T00:00:00", 1.0)
    for i in range(5):
        e.add_occurrence("Quantum", "2024-01-01T00:00:00", 2.0 + i * 0.5)
    trending = e.get_trending(5)
    print("  Trending: " + str([(t.term, round(t.score, 2)) for t in trending]))
    emerging = e.get_emerging(3)
    print("  Emerging: " + str([(t.term, round(t.velocity, 2)) for t in emerging]))
    print("  Stats: " + str(e.get_stats()))
    print("Trending Engine test complete.")

if __name__ == "__main__":
    run()
