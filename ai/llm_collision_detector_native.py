"""LLM Collision Detector — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

@dataclass
class Bounds:
    x: float
    y: float
    width: float
    height: float

    def right(self) -> float:
        return self.x + self.width

    def bottom(self) -> float:
        return self.y + self.height

    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

class CollisionDetector:
    def __init__(self) -> None:
        self._pairs: List[Tuple[str, str]] = []

    def aabb(self, a: Bounds, b: Bounds) -> bool:
        return a.x < b.right() and a.right() > b.x and a.y < b.bottom() and a.bottom() > b.y

    def check(self, objects: Dict[str, Bounds]) -> List[Tuple[str, str]]:
        collisions = []
        ids = list(objects.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if self.aabb(objects[ids[i]], objects[ids[j]]):
                    collisions.append((ids[i], ids[j]))
        self._pairs = collisions
        return collisions

    def check_point(self, point: Tuple[float, float], bounds: Bounds) -> bool:
        return bounds.x <= point[0] <= bounds.right() and bounds.y <= point[1] <= bounds.bottom()

    def check_circle(self, c1: Tuple[float, float, float], c2: Tuple[float, float, float]) -> bool:
        dx = c1[0] - c2[0]
        dy = c1[1] - c2[1]
        distance = (dx * dx + dy * dy) ** 0.5
        return distance < c1[2] + c2[2]

    def get_stats(self) -> Dict[str, Any]:
        return {"collisions": len(self._pairs)}

def run() -> None:
    print("Collision Detector test")
    e = CollisionDetector()
    objs = {"a": Bounds(0, 0, 10, 10), "b": Bounds(5, 5, 10, 10), "c": Bounds(20, 20, 5, 5)}
    collisions = e.check(objs)
    print("  Collisions: " + str(collisions))
    print("  Point in A: " + str(e.check_point((5, 5), objs["a"])))
    print("  Circle collision: " + str(e.check_circle((0, 0, 5), (3, 4, 5))))
    print("  Stats: " + str(e.get_stats()))
    print("Collision Detector test complete.")

if __name__ == "__main__":
    run()
