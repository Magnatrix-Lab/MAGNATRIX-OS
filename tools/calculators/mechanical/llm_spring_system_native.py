"""Spring System — Hooke's law, dampening, constraints, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class MassPoint:
    position: Tuple[float, float]
    velocity: Tuple[float, float] = (0.0, 0.0)
    mass: float = 1.0
    fixed: bool = False

@dataclass
class Spring:
    a: int
    b: int
    rest_length: float
    stiffness: float
    damping: float

class SpringSystem:
    def __init__(self):
        self.points: List[MassPoint] = []
        self.springs: List[Spring] = []

    def add_point(self, point: MassPoint) -> int:
        self.points.append(point)
        return len(self.points) - 1

    def add_spring(self, spring: Spring):
        self.springs.append(spring)

    def update(self, dt: float):
        forces = [(0.0, 0.0) for _ in self.points]
        for spring in self.springs:
            p1 = self.points[spring.a]
            p2 = self.points[spring.b]
            dx = p2.position[0] - p1.position[0]
            dy = p2.position[1] - p1.position[1]
            dist = math.sqrt(dx*dx + dy*dy) + 1e-6
            force_mag = spring.stiffness * (dist - spring.rest_length)
            fx = (dx / dist) * force_mag
            fy = (dy / dist) * force_mag
            # Damping
            dvx = p2.velocity[0] - p1.velocity[0]
            dvy = p2.velocity[1] - p1.velocity[1]
            fx += spring.damping * (dvx * dx / dist)
            fy += spring.damping * (dvy * dy / dist)
            forces[spring.a] = (forces[spring.a][0] + fx, forces[spring.a][1] + fy)
            forces[spring.b] = (forces[spring.b][0] - fx, forces[spring.b][1] - fy)
        for i, p in enumerate(self.points):
            if p.fixed:
                continue
            ax = forces[i][0] / p.mass
            ay = forces[i][1] / p.mass
            vx = p.velocity[0] + ax * dt
            vy = p.velocity[1] + ay * dt
            px = p.position[0] + vx * dt
            py = p.position[1] + vy * dt
            self.points[i] = MassPoint((px, py), (vx, vy), p.mass, p.fixed)

    def stats(self) -> Dict:
        return {"points": len(self.points), "springs": len(self.springs)}

def run():
    ss = SpringSystem()
    p0 = ss.add_point(MassPoint((0, 0), fixed=True))
    p1 = ss.add_point(MassPoint((5, 0)))
    p2 = ss.add_point(MassPoint((10, 0)))
    ss.add_spring(Spring(p0, p1, 5, 10, 0.5))
    ss.add_spring(Spring(p1, p2, 5, 10, 0.5))
    for _ in range(100):
        ss.update(0.01)
    print(ss.stats())
    for p in ss.points:
        print(p.position)

if __name__ == "__main__":
    run()
