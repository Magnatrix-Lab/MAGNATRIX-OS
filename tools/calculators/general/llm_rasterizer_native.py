"""Rasterizer — triangle mesh, scanline, barycentric, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class Vec3:
    x: float; y: float; z: float
    def __add__(self, o): return Vec3(self.x+o.x, self.y+o.y, self.z+o.z)
    def __sub__(self, o): return Vec3(self.x-o.x, self.y-o.y, self.z-o.z)
    def __mul__(self, s): return Vec3(self.x*s, self.y*s, self.z*s)

@dataclass
class Triangle:
    v0: Vec3; v1: Vec3; v2: Vec3
    color: Tuple[int, int, int] = (255, 255, 255)

class Rasterizer:
    def __init__(self, width: int = 64, height: int = 64):
        self.width = width
        self.height = height
        self.buffer = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]
        self.triangles: List[Triangle] = []

    def add_triangle(self, tri: Triangle):
        self.triangles.append(tri)

    def _edge(self, a: Vec3, b: Vec3, c: Vec3) -> float:
        return (c.x - a.x) * (b.y - a.y) - (c.y - a.y) * (b.x - a.x)

    def _rasterize_triangle(self, tri: Triangle):
        min_x = max(0, int(min(tri.v0.x, tri.v1.x, tri.v2.x)))
        max_x = min(self.width - 1, int(max(tri.v0.x, tri.v1.x, tri.v2.x)))
        min_y = max(0, int(min(tri.v0.y, tri.v1.y, tri.v2.y)))
        max_y = min(self.height - 1, int(max(tri.v0.y, tri.v1.y, tri.v2.y)))
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                p = Vec3(x + 0.5, y + 0.5, 0)
                w0 = self._edge(tri.v1, tri.v2, p)
                w1 = self._edge(tri.v2, tri.v0, p)
                w2 = self._edge(tri.v0, tri.v1, p)
                if w0 >= 0 and w1 >= 0 and w2 >= 0:
                    self.buffer[y][x] = tri.color

    def render(self):
        for tri in self.triangles:
            self._rasterize_triangle(tri)
        return self.buffer

    def clear(self):
        self.buffer = [[(0, 0, 0) for _ in range(self.width)] for _ in range(self.height)]

    def stats(self) -> Dict:
        return {"width": self.width, "height": self.height, "triangles": len(self.triangles)}

def run():
    r = Rasterizer(32, 32)
    r.add_triangle(Triangle(Vec3(5, 5, 0), Vec3(20, 5, 0), Vec3(12, 25, 0), (255, 0, 0)))
    r.add_triangle(Triangle(Vec3(15, 15, 0), Vec3(28, 15, 0), Vec3(22, 28, 0), (0, 255, 0)))
    buf = r.render()
    print("Rendered", len(buf), "x", len(buf[0]))
    print(r.stats())

if __name__ == "__main__":
    run()
