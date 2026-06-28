#!/usr/bin/env python3
"""Autonomous Vehicle Controller for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0
    def distance(self, other: 'Point') -> float:
        return math.sqrt((self.x-other.x)**2 + (self.y-other.y)**2)
    def to_dict(self): return {"x": self.x, "y": self.y}

class PathPlanner:
    def __init__(self):
        self.waypoints: List[Point] = []
    def add_waypoint(self, p: Point):
        self.waypoints.append(p)
    def plan(self, start: Point, goal: Point) -> List[Point]:
        return [start] + self.waypoints + [goal]
    def to_dict(self): return {"waypoints": len(self.waypoints)}

class AutonomousVehicleController:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.planner = PathPlanner()
        self.position = Point()
    def move_to(self, target: Point) -> Dict[str, Any]:
        dist = self.position.distance(target)
        self.position = target
        return {"distance": round(dist, 2), "new_position": self.position.to_dict()}
    def to_dict(self): return {"position": self.position.to_dict(), "waypoints": self.planner.to_dict()}
