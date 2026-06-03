"""LLM Level Manager — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class LevelState(Enum):
    LOCKED = auto()
    UNLOCKED = auto()
    COMPLETED = auto()
    SKIPPED = auto()

@dataclass
class Level:
    id: str
    name: str
    difficulty: int
    required_score: int
    state: LevelState = LevelState.LOCKED
    best_score: int = 0
    stars: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class LevelManager:
    def __init__(self) -> None:
        self._levels: Dict[str, Level] = {}
        self._level_order: List[str] = []

    def add_level(self, level: Level) -> None:
        self._levels[level.id] = level
        if level.id not in self._level_order:
            self._level_order.append(level.id)

    def unlock(self, level_id: str) -> bool:
        level = self._levels.get(level_id)
        if level:
            level.state = LevelState.UNLOCKED
            return True
        return False

    def complete(self, level_id: str, score: int, stars: int = 0) -> bool:
        level = self._levels.get(level_id)
        if level and level.state in (LevelState.UNLOCKED, LevelState.COMPLETED):
            level.state = LevelState.COMPLETED
            if score > level.best_score:
                level.best_score = score
            if stars > level.stars:
                level.stars = stars
            self._unlock_next(level_id)
            return True
        return False

    def _unlock_next(self, level_id: str) -> None:
        if level_id in self._level_order:
            idx = self._level_order.index(level_id)
            if idx + 1 < len(self._level_order):
                next_id = self._level_order[idx + 1]
                self.unlock(next_id)

    def get_progress(self) -> Dict[str, Any]:
        completed = sum(1 for l in self._levels.values() if l.state == LevelState.COMPLETED)
        total = len(self._levels)
        return {"completed": completed, "total": total, "percent": completed / total * 100 if total > 0 else 0}

    def get_stars_total(self) -> int:
        return sum(l.stars for l in self._levels.values())

    def get_stats(self) -> Dict[str, Any]:
        states = {}
        for l in self._levels.values():
            states[l.state.name] = states.get(l.state.name, 0) + 1
        return {"levels": len(self._levels), "progress": self.get_progress(), "stars": self.get_stars_total(), "by_state": states}

def run() -> None:
    print("Level Manager test")
    e = LevelManager()
    e.add_level(Level("l1", "Level 1", 1, 0, LevelState.UNLOCKED))
    e.add_level(Level("l2", "Level 2", 2, 100))
    e.add_level(Level("l3", "Level 3", 3, 200))
    e.complete("l1", 150, 3)
    print("  After L1 complete: " + str(e._levels["l2"].state.name))
    e.complete("l2", 250, 2)
    print("  Progress: " + str(e.get_progress()))
    print("  Total stars: " + str(e.get_stars_total()))
    print("  Stats: " + str(e.get_stats()))
    print("Level Manager test complete.")

if __name__ == "__main__":
    run()
