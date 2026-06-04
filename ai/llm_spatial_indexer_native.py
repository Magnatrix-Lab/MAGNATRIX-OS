"""Spatial Indexer - R-tree style spatial indexing for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto
import math

@dataclass
class BoundingBox:
    min_x: float; min_y: float; max_x: float; max_y: float
    
    def intersects(self, other: "BoundingBox") -> bool:
        return (self.min_x <= other.max_x and self.max_x >= other.min_x and
                self.min_y <= other.max_y and self.max_y >= other.min_y)
    
    def contains(self, x: float, y: float) -> bool:
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

@dataclass
class SpatialEntry:
    id: str
    bbox: BoundingBox
    data: any = None

@dataclass
class SpatialIndexer:
    entries: List[SpatialEntry] = field(default_factory=list)
    
    def insert(self, id: str, min_x: float, min_y: float, max_x: float, max_y: float, data: any = None) -> None:
        self.entries.append(SpatialEntry(id, BoundingBox(min_x, min_y, max_x, max_y), data))
    
    def query(self, min_x: float, min_y: float, max_x: float, max_y: float) -> List[str]:
        query_bbox = BoundingBox(min_x, min_y, max_x, max_y)
        return [e.id for e in self.entries if e.bbox.intersects(query_bbox)]
    
    def nearest(self, x: float, y: float, k: int = 1) -> List[Tuple[str, float]]:
        distances = []
        for e in self.entries:
            cx = (e.bbox.min_x + e.bbox.max_x) / 2
            cy = (e.bbox.min_y + e.bbox.max_y) / 2
            dist = math.sqrt((cx - x)**2 + (cy - y)**2)
            distances.append((e.id, dist))
        distances.sort(key=lambda x: x[1])
        return distances[:k]
    
    def stats(self) -> dict:
        return {"entries": len(self.entries)}

def run():
    si = SpatialIndexer()
    si.insert("A", 0, 0, 10, 10)
    si.insert("B", 5, 5, 15, 15)
    si.insert("C", 20, 20, 30, 30)
    print("Query (3,3,12,12):", si.query(3, 3, 12, 12))
    print("Nearest to (0,0):", si.nearest(0, 0, 2))
    print("Stats:", si.stats())

if __name__ == "__main__": run()
