"""SLAM Engine — occupancy grid, landmark detection, pose estimation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import math

@dataclass
class Landmark:
    id: int
    x: float
    y: float

@dataclass
class SLAM:
    grid_size: float = 0.1
    occupancy: Dict[Tuple[int, int], float] = field(default_factory=dict)
    landmarks: List[Landmark] = field(default_factory=list)
    pose: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    """x, y, theta in radians"""

    def observe(self, sensor_readings: List[Tuple[float, float]]):
        x, y, theta = self.pose
        for r, phi in sensor_readings:
            gx = x + r * math.cos(theta + phi)
            gy = y + r * math.sin(theta + phi)
            cell = (int(gx / self.grid_size), int(gy / self.grid_size))
            self.occupancy[cell] = min(1.0, self.occupancy.get(cell, 0.0) + 0.3)
            free = (int((x + 0.5 * r * math.cos(theta + phi)) / self.grid_size), int((y + 0.5 * r * math.sin(theta + phi)) / self.grid_size))
            self.occupancy[free] = max(0.0, self.occupancy.get(free, 0.0) - 0.1)

    def move(self, dx: float, dy: float, dtheta: float):
        x, y, theta = self.pose
        self.pose = (x + dx, y + dy, theta + dtheta)

    def detect_landmarks(self, threshold: float = 0.7) -> List[Landmark]:
        detected = []
        for i, (cell, occ) in enumerate(self.occupancy.items()):
            if occ > threshold:
                detected.append(Landmark(i, cell[0] * self.grid_size, cell[1] * self.grid_size))
        return detected

    def stats(self) -> Dict:
        return {"cells": len(self.occupancy), "landmarks": len(self.landmarks), "pose": self.pose}

def run():
    slam = SLAM()
    slam.observe([(1.0, 0.0), (2.0, 0.5)])
    slam.move(0.1, 0, 0)
    slam.observe([(0.9, -0.1), (1.9, 0.4)])
    print(slam.stats())

if __name__ == "__main__":
    run()
