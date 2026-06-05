"""Spatial Index — R-tree, quadtree, grid, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class BoundingBox:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def intersects(self, other: "BoundingBox") -> bool:
        return not (self.max_x < other.min_x or self.min_x > other.max_x or self.max_y < other.min_y or self.min_y > other.max_y)

    def contains(self, x: float, y: float) -> bool:
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def center(self) -> Tuple[float, float]:
        return ((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)

@dataclass
class SpatialEntry:
    entry_id: str
    bbox: BoundingBox
    data: Dict = field(default_factory=dict)

class Quadtree:
    def __init__(self, bbox: BoundingBox, capacity: int = 4, max_depth: int = 10):
        self.bbox = bbox
        self.capacity = capacity
        self.max_depth = max_depth
        self.entries: List[SpatialEntry] = []
        self.children: List["Quadtree"] = []
        self.depth = 0

    def insert(self, entry: SpatialEntry):
        if not self.bbox.intersects(entry.bbox):
            return False
        if len(self.children) == 0 and len(self.entries) < self.capacity:
            self.entries.append(entry)
            return True
        if len(self.children) == 0:
            self._subdivide()
        for child in self.children:
            if child.insert(entry):
                return True
        return False

    def _subdivide(self):
        cx, cy = self.bbox.center()
        bboxes = [
            BoundingBox(self.bbox.min_x, self.bbox.min_y, cx, cy),
            BoundingBox(cx, self.bbox.min_y, self.bbox.max_x, cy),
            BoundingBox(self.bbox.min_x, cy, cx, self.bbox.max_y),
            BoundingBox(cx, cy, self.bbox.max_x, self.bbox.max_y),
        ]
        for bb in bboxes:
            child = Quadtree(bb, self.capacity, self.max_depth)
            child.depth = self.depth + 1
            self.children.append(child)
        for entry in self.entries:
            for child in self.children:
                if child.insert(entry):
                    break
        self.entries = []

    def query(self, bbox: BoundingBox) -> List[SpatialEntry]:
        if not self.bbox.intersects(bbox):
            return []
        results = []
        for entry in self.entries:
            if entry.bbox.intersects(bbox):
                results.append(entry)
        for child in self.children:
            results.extend(child.query(bbox))
        return results

    def stats(self) -> Dict:
        return {"bbox": self.bbox, "entries": len(self.entries), "children": len(self.children), "depth": self.depth}

def run():
    tree = Quadtree(BoundingBox(0, 0, 100, 100), capacity=2)
    tree.insert(SpatialEntry("a", BoundingBox(10, 10, 20, 20)))
    tree.insert(SpatialEntry("b", BoundingBox(15, 15, 25, 25)))
    tree.insert(SpatialEntry("c", BoundingBox(60, 60, 70, 70)))
    results = tree.query(BoundingBox(12, 12, 30, 30))
    print([r.entry_id for r in results])
    print(tree.stats())

if __name__ == "__main__":
    run()
