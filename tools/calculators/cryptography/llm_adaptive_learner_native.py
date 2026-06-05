"""Adaptive Learner — spaced repetition, mastery, difficulty adjustment, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Item:
    id: str
    difficulty: float = 0.5
    mastery: float = 0.0
    last_review: float = 0.0
    interval: float = 1.0

class AdaptiveLearner:
    def __init__(self):
        self.items: Dict[str, Item] = {}

    def add_item(self, item: Item):
        self.items[item.id] = item

    def review(self, item_id: str, correct: bool, current_time: float):
        item = self.items.get(item_id)
        if not item:
            return
        if correct:
            item.interval *= 2.5
            item.mastery = min(1.0, item.mastery + 0.2)
        else:
            item.interval = 1.0
            item.mastery = max(0.0, item.mastery - 0.1)
        item.last_review = current_time

    def due_items(self, current_time: float) -> List[str]:
        return [i.id for i in self.items.values() if current_time - i.last_review >= i.interval]

    def next_item(self, current_time: float) -> Optional[str]:
        due = [i for i in self.items.values() if current_time - i.last_review >= i.interval]
        if not due:
            return None
        return min(due, key=lambda i: i.mastery).id

    def estimated_mastery(self, item_id: str, current_time: float) -> float:
        item = self.items.get(item_id)
        if not item:
            return 0.0
        elapsed = current_time - item.last_review
        decay = math.exp(-elapsed / (item.interval + 1))
        return item.mastery * decay

    def stats(self) -> Dict:
        return {"items": len(self.items), "avg_mastery": sum(i.mastery for i in self.items.values()) / len(self.items) if self.items else 0}

def run():
    al = AdaptiveLearner()
    al.add_item(Item("A"))
    al.review("A", True, 0)
    al.review("A", True, 3)
    print("Due at 5:", al.due_items(5))
    print("Mastery:", al.estimated_mastery("A", 5))
    print(al.stats())

if __name__ == "__main__":
    run()
