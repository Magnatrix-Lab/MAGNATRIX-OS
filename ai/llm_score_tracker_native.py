"""LLM Score Tracker — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime

@dataclass
class ScoreEntry:
    player_id: str
    score: int
    level: int
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class ScoreTracker:
    def __init__(self) -> None:
        self._entries: List[ScoreEntry] = []
        self._high_scores: Dict[str, int] = {}
        self._player_totals: Dict[str, int] = {}

    def add_score(self, entry: ScoreEntry) -> None:
        self._entries.append(entry)
        if entry.player_id not in self._high_scores or entry.score > self._high_scores[entry.player_id]:
            self._high_scores[entry.player_id] = entry.score
        self._player_totals[entry.player_id] = self._player_totals.get(entry.player_id, 0) + entry.score

    def get_high_score(self, player_id: str) -> int:
        return self._high_scores.get(player_id, 0)

    def get_global_high_score(self) -> Optional[Tuple[str, int]]:
        if not self._high_scores:
            return None
        return max(self._high_scores.items(), key=lambda x: x[1])

    def get_leaderboard(self, n: int = 10) -> List[Tuple[str, int]]:
        sorted_scores = sorted(self._high_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:n]

    def get_player_total(self, player_id: str) -> int:
        return self._player_totals.get(player_id, 0)

    def get_average_score(self, player_id: Optional[str] = None) -> float:
        if player_id:
            entries = [e for e in self._entries if e.player_id == player_id]
        else:
            entries = self._entries
        if not entries:
            return 0.0
        return sum(e.score for e in entries) / len(entries)

    def get_stats(self) -> Dict[str, Any]:
        return {"entries": len(self._entries), "players": len(self._high_scores), "avg_score": self.get_average_score(), "global_high": self.get_global_high_score()}

def run() -> None:
    print("Score Tracker test")
    e = ScoreTracker()
    e.add_score(ScoreEntry("p1", 100, 1, "2024-01-01T00:00:00"))
    e.add_score(ScoreEntry("p2", 150, 1, "2024-01-01T00:00:00"))
    e.add_score(ScoreEntry("p1", 200, 2, "2024-01-01T00:00:00"))
    e.add_score(ScoreEntry("p3", 300, 1, "2024-01-01T00:00:00"))
    print("  Leaderboard: " + str(e.get_leaderboard(3)))
    print("  P1 high: " + str(e.get_high_score("p1")))
    print("  P1 total: " + str(e.get_player_total("p1")))
    print("  Global high: " + str(e.get_global_high_score()))
    print("  Stats: " + str(e.get_stats()))
    print("Score Tracker test complete.")

if __name__ == "__main__":
    run()
