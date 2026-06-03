"""Kinematics Solver - 2D forward kinematics for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import math

@dataclass
class KinematicsSolver:
    link_lengths: List[float] = None

    def __post_init__(self):
        if self.link_lengths is None: self.link_lengths = [1.0, 1.0]

    def forward(self, angles: List[float]) -> List[Tuple[float,float]]:
        points = [(0.0, 0.0)]
        x, y, theta = 0.0, 0.0, 0.0
        for i, a in enumerate(angles):
            theta += a
            x += self.link_lengths[i] * math.cos(theta)
            y += self.link_lengths[i] * math.sin(theta)
            points.append((round(x,4), round(y,4)))
        return points

    def stats(self, angles: List[float]) -> dict:
        points = self.forward(angles)
        end = points[-1]
        return {"links": len(self.link_lengths), "end_effector": end, "reach": round(math.sqrt(end[0]**2 + end[1]**2), 4)}

def run():
    ks = KinematicsSolver([1.0, 1.0])
    points = ks.forward([0.5, 0.5])
    print("Points:", points)
    print("Stats:", ks.stats([0.5, 0.5]))

if __name__ == "__main__": run()
