"""Collision Engine — AABB, circle, SAT, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class Vec2:
    x: float; y: float
    def __add__(self, o): return Vec2(self.x+o.x, self.y+o.y)
    def __sub__(self, o): return Vec2(self.x-o.x, self.y-o.y)
    def __mul__(self, s): return Vec2(self.x*s, self.y*s)
    def dot(self, o): return self.x*o.x + self.y*o.y

@dataclass
class AABB:
    min: Vec2
    max: Vec2

@dataclass
class Circle:
    center: Vec2
    radius: float

class CollisionEngine:
    def __init__(self):
        self.collisions: List[Dict] = []

    def aabb_aabb(self, a: AABB, b: AABB) -> bool:
        return a.min.x <= b.max.x and a.max.x >= b.min.x and a.min.y <= b.max.y and a.max.y >= b.min.y

    def circle_circle(self, a: Circle, b: Circle) -> bool:
        dx = a.center.x - b.center.x
        dy = a.center.y - b.center.y
        dist = math.sqrt(dx*dx + dy*dy)
        return dist <= a.radius + b.radius

    def point_aabb(self, p: Vec2, box: AABB) -> bool:
        return box.min.x <= p.x <= box.max.x and box.min.y <= p.y <= box.max.y

    def point_circle(self, p: Vec2, c: Circle) -> bool:
        dx = p.x - c.center.x
        dy = p.y - c.center.y
        return math.sqrt(dx*dx + dy*dy) <= c.radius

    def aabb_circle(self, box: AABB, c: Circle) -> bool:
        closest = Vec2(max(box.min.x, min(c.center.x, box.max.x)), max(box.min.y, min(c.center.y, box.max.y)))
        dx = closest.x - c.center.x
        dy = closest.y - c.center.y
        return dx*dx + dy*dy <= c.radius * c.radius

    def resolve_collision(self, a, b) -> Optional[Dict]:
        result = None
        if isinstance(a, AABB) and isinstance(b, AABB):
            if self.aabb_aabb(a, b):
                result = {"type": "AABB-AABB", "collided": True}
        elif isinstance(a, Circle) and isinstance(b, Circle):
            if self.circle_circle(a, b):
                result = {"type": "Circle-Circle", "collided": True}
        elif isinstance(a, AABB) and isinstance(b, Circle):
            if self.aabb_circle(a, b):
                result = {"type": "AABB-Circle", "collided": True}
        elif isinstance(a, Circle) and isinstance(b, AABB):
            if self.aabb_circle(b, a):
                result = {"type": "Circle-AABB", "collided": True}
        if result:
            self.collisions.append(result)
        return result

    def stats(self) -> Dict:
        return {"collisions": len(self.collisions)}

def run():
    ce = CollisionEngine()
    a = AABB(Vec2(0, 0), Vec2(10, 10))
    b = AABB(Vec2(5, 5), Vec2(15, 15))
    c = Circle(Vec2(20, 20), 3)
    d = Circle(Vec2(8, 8), 5)
    print(ce.resolve_collision(a, b))
    print(ce.resolve_collision(c, d))
    print(ce.resolve_collision(a, d))
    print(ce.stats())

if __name__ == "__main__":
    run()
