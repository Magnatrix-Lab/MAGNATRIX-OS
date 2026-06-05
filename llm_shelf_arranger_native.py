"""Shelf Arranger — classification, spine labels, face-out, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ShelfItem:
    id: str
    title: str
    call_number: str
    height_cm: float
    width_cm: float

class ShelfArranger:
    def __init__(self):
        self.items: List[ShelfItem] = []
        self.shelf_width: float = 90.0

    def add_item(self, item: ShelfItem):
        self.items.append(item)

    def sort_by_call_number(self) -> List[ShelfItem]:
        return sorted(self.items, key=lambda x: x.call_number)

    def face_out_candidates(self, min_width: float = 20.0) -> List[ShelfItem]:
        return [i for i in self.items if i.width_cm >= min_width]

    def shelf_assignment(self, items_per_shelf: int = 30) -> Dict[int, List[str]]:
        sorted_items = self.sort_by_call_number()
        shelves = {}
        for i, item in enumerate(sorted_items):
            shelf_num = i // items_per_shelf + 1
            shelves.setdefault(shelf_num, []).append(item.id)
        return shelves

    def total_width(self) -> float:
        return sum(i.width_cm for i in self.items)

    def shelves_needed(self) -> int:
        return int(self.total_width() / self.shelf_width) + 1

    def stats(self) -> Dict:
        return {"items": len(self.items), "total_width": round(self.total_width(), 1), "shelves": self.shelves_needed()}

def run():
    sa = ShelfArranger()
    sa.add_item(ShelfItem("1", "A", "QA76.5", 25, 3))
    sa.add_item(ShelfItem("2", "B", "QA76.7", 25, 3))
    sa.add_item(ShelfItem("3", "C", "QA77.1", 25, 3))
    print(sa.stats())
    print("Shelves:", sa.shelf_assignment(2))

if __name__ == "__main__":
    run()
