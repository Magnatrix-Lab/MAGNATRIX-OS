"""Interactive Teacher — adaptive curriculum & spaced repetition, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import time

class Difficulty(Enum):
    EASY = auto()
    MEDIUM = auto()
    HARD = auto()

@dataclass
class LearningItem:
    item_id: str
    content: Dict
    difficulty: Difficulty
    mastery: float = 0.0
    last_reviewed: float = 0.0
    review_count: int = 0

class InteractiveTeacher:
    def __init__(self, student_level: float = 0.5):
        self.student_level = student_level
        self.items: Dict[str, LearningItem] = {}
        self.history: List[Dict] = []
        self.interactions: int = 0

    def add_item(self, item_id: str, content: Dict, difficulty: Difficulty):
        self.items[item_id] = LearningItem(item_id, content, difficulty)

    def _difficulty_value(self, d: Difficulty) -> float:
        return {"EASY": 0.3, "MEDIUM": 0.6, "HARD": 0.9}.get(d.name, 0.5)

    def _select_next(self) -> Optional[LearningItem]:
        candidates = [i for i in self.items.values() if i.mastery < 0.95]
        if not candidates:
            return None
        scored = []
        for c in candidates:
            time_factor = 1.0 / (1 + time.time() - c.last_reviewed)
            need = (1 - c.mastery) * self._difficulty_value(c.difficulty) * time_factor
            scored.append((need, c))
        scored.sort(reverse=True)
        return scored[0][1]

    def present(self, item_id: str, performance: float):
        item = self.items.get(item_id)
        if not item:
            return
        item.review_count += 1
        item.last_reviewed = time.time()
        item.mastery = min(1.0, item.mastery + performance * (1 - item.mastery) * 0.3)
        self.student_level = 0.9 * self.student_level + 0.1 * performance
        self.history.append({"item": item_id, "performance": performance, "mastery": item.mastery})
        self.interactions += 1

    def get_next_lesson(self) -> Optional[Dict]:
        item = self._select_next()
        if not item:
            return None
        return {"item_id": item.item_id, "difficulty": item.difficulty.name, "mastery": item.mastery, "content": item.content}

    def stats(self) -> Dict:
        avg_mastery = sum(i.mastery for i in self.items.values()) / len(self.items) if self.items else 0
        return {"items": len(self.items), "interactions": self.interactions, "student_level": self.student_level, "avg_mastery": avg_mastery}

def run():
    teacher = InteractiveTeacher(student_level=0.4)
    for i in range(10):
        d = Difficulty.EASY if i < 3 else (Difficulty.MEDIUM if i < 6 else Difficulty.HARD)
        teacher.add_item(f"item_{i}", {"concept": f"topic_{i}"}, d)
    for _ in range(15):
        lesson = teacher.get_next_lesson()
        if lesson:
            teacher.present(lesson["item_id"], random.random() * 0.8 + 0.2)
    print(teacher.stats())

if __name__ == "__main__":
    run()
