"""Autonomous Navigator — lane, obstacle, decision, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Obstacle:
    x: float
    y: float
    width: float
    speed: float = 0.0

class AutonomousNavigator:
    def __init__(self):
        self.lane_width: float = 3.5
        self.vehicle_width: float = 1.8
        self.position: float = 0.0
        """lateral offset from lane center"""
        self.obstacles: List[Obstacle] = []

    def add_obstacle(self, o: Obstacle):
        self.obstacles.append(o)

    def lane_boundary(self) -> Tuple[float, float]:
        half = self.lane_width / 2 - self.vehicle_width / 2
        return -half, half

    def in_lane(self) -> bool:
        left, right = self.lane_boundary()
        return left <= self.position <= right

    def distance_to(self, o: Obstacle) -> float:
        return math.sqrt(o.x**2 + (o.y - self.position)**2)

    def time_to_collision(self, o: Obstacle, vehicle_speed: float = 20.0) -> float:
        rel_speed = vehicle_speed - o.speed
        if rel_speed <= 0:
            return float('inf')
        return o.x / rel_speed

    def safe_to_lane_change(self, direction: str, vehicle_speed: float = 20.0) -> bool:
        target = self.position + (self.lane_width if direction == "left" else -self.lane_width)
        for o in self.obstacles:
            if abs(o.y - target) < self.vehicle_width and o.x > 0 and o.x < 50:
                return False
        return True

    def recommended_action(self, vehicle_speed: float = 20.0) -> str:
        closest = min(self.obstacles, key=lambda o: self.distance_to(o), default=None)
        if closest and self.time_to_collision(closest, vehicle_speed) < 3.0:
            if self.safe_to_lane_change("left", vehicle_speed):
                return "change_left"
            elif self.safe_to_lane_change("right", vehicle_speed):
                return "change_right"
            return "brake"
        return "maintain"

    def stats(self) -> Dict:
        return {
            "in_lane": self.in_lane(),
            "obstacles": len(self.obstacles),
            "action": self.recommended_action()
        }

def run():
    an = AutonomousNavigator()
    an.add_obstacle(Obstacle(30, 0, 1.8, 15))
    an.add_obstacle(Obstacle(100, 3.5, 1.8, 10))
    print(an.stats())

if __name__ == "__main__":
    run()
