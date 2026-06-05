"""Odometry Tracker — wheel encoder, pose estimation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class Pose:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0

class OdometryTracker:
    def __init__(self, wheel_radius: float = 0.1, wheel_base: float = 0.5):
        self.wheel_radius = wheel_radius
        self.wheel_base = wheel_base
        self.pose = Pose()
        self.left_ticks = 0
        self.right_ticks = 0
        self.ticks_per_rev = 360
        self.history: List[Pose] = []

    def update(self, left_ticks: int, right_ticks: int) -> Pose:
        dl = 2 * math.pi * self.wheel_radius * (left_ticks - self.left_ticks) / self.ticks_per_rev
        dr = 2 * math.pi * self.wheel_radius * (right_ticks - self.right_ticks) / self.ticks_per_rev
        self.left_ticks = left_ticks
        self.right_ticks = right_ticks
        dc = (dl + dr) / 2
        dtheta = (dr - dl) / self.wheel_base
        self.pose.theta += dtheta
        self.pose.x += dc * math.cos(self.pose.theta)
        self.pose.y += dc * math.sin(self.pose.theta)
        self.history.append(Pose(self.pose.x, self.pose.y, self.pose.theta))
        return self.pose

    def distance_traveled(self) -> float:
        if len(self.history) < 2:
            return 0.0
        total = 0.0
        for i in range(1, len(self.history)):
            dx = self.history[i].x - self.history[i-1].x
            dy = self.history[i].y - self.history[i-1].y
            total += math.sqrt(dx**2 + dy**2)
        return total

    def stats(self) -> Dict:
        return {"pose": (self.pose.x, self.pose.y, self.pose.theta), "distance": self.distance_traveled(), "history": len(self.history)}

def run():
    odo = OdometryTracker(0.1, 0.5)
    odo.update(360, 360)
    odo.update(720, 720)
    odo.update(1080, 900)
    print(odo.stats())

if __name__ == "__main__":
    run()
