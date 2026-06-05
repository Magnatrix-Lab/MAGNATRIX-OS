"""Depth of Field — hyperfocal, near, far, circle of confusion, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class DepthOfField:
    focal_length: float = 50.0
    aperture: float = 2.8
    subject_distance: float = 3.0
    circle_of_confusion: float = 0.03
    """mm"""

    def hyperfocal(self) -> float:
        if self.aperture <= 0 or self.circle_of_confusion <= 0:
            return 0.0
        return (self.focal_length ** 2) / (self.aperture * self.circle_of_confusion) + self.focal_length

    def near_limit(self) -> float:
        h = self.hyperfocal()
        if h <= self.focal_length:
            return 0.0
        return (h * self.subject_distance) / (h + self.subject_distance - self.focal_length)

    def far_limit(self) -> float:
        h = self.hyperfocal()
        if h <= self.focal_length:
            return float('inf')
        denom = h - self.subject_distance + self.focal_length
        if denom <= 0:
            return float('inf')
        return (h * self.subject_distance) / denom

    def total_dof(self) -> float:
        far = self.far_limit()
        if far == float('inf'):
            return float('inf')
        return far - self.near_limit()

    def in_focus(self, distance: float) -> bool:
        return self.near_limit() <= distance <= self.far_limit()

    def stats(self) -> Dict:
        return {"hyperfocal": round(self.hyperfocal(), 1), "near": round(self.near_limit(), 2), "far": round(self.far_limit(), 2) if self.far_limit() != float('inf') else 'inf', "dof": round(self.total_dof(), 2) if self.total_dof() != float('inf') else 'inf'}

def run():
    dof = DepthOfField(focal_length=85, aperture=1.8, subject_distance=5)
    print(dof.stats())
    print("In focus at 4m:", dof.in_focus(4))

if __name__ == "__main__":
    run()
