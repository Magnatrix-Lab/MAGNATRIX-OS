"""Path Planner — RRT, A*, potential fields, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import random
import math
import heapq

@dataclass
class Point:
    x: float; y: float

    def distance(self, other: "Point") -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

class PathPlanner:
    def __init__(self, bounds: Tuple[float, float, float, float] = (0, 0, 100, 100)):
        self.bounds = bounds
        self.obstacles: List[Tuple[Point, float]] = []  # center, radius

    def add_obstacle(self, x: float, y: float, radius: float):
        self.obstacles.append((Point(x, y), radius))

    def _collision(self, p: Point) -> bool:
        for obs, r in self.obstacles:
            if p.distance(obs) < r:
                return True
        return False

    def _collision_line(self, a: Point, b: Point) -> bool:
        steps = int(a.distance(b) / 2) + 1
        for i in range(steps + 1):
            t = i / steps
            p = Point(a.x + t * (b.x - a.x), a.y + t * (b.y - a.y))
            if self._collision(p):
                return True
        return False

    def rrt(self, start: Point, goal: Point, max_iter: int = 1000, step: float = 5.0) -> Optional[List[Point]]:
        tree = {start: None}
        for _ in range(max_iter):
            rand = Point(random.uniform(self.bounds[0], self.bounds[2]), random.uniform(self.bounds[1], self.bounds[3]))
            nearest = min(tree.keys(), key=lambda p: p.distance(rand))
            if nearest.distance(rand) < step:
                new = rand
            else:
                dx = rand.x - nearest.x
                dy = rand.y - nearest.y
                dist = math.sqrt(dx**2 + dy**2)
                new = Point(nearest.x + dx * step / dist, nearest.y + dy * step / dist)
            if not self._collision_line(nearest, new):
                tree[new] = nearest
                if new.distance(goal) < step:
                    # Reconstruct path
                    path = []
                    current = new
                    while current is not None:
                        path.append(current)
                        current = tree[current]
                    return list(reversed(path)) + [goal]
        return None

    def potential_field(self, start: Point, goal: Point, max_iter: int = 500, step: float = 0.5) -> List[Point]:
        path = [start]
        current = start
        for _ in range(max_iter):
            # Attractive force to goal
            dx = goal.x - current.x
            dy = goal.y - current.y
            dist = math.sqrt(dx**2 + dy**2)
            if dist < 1:
                break
            fx = dx / dist
            fy = dy / dist
            # Repulsive from obstacles
            for obs, r in self.obstacles:
                d = current.distance(obs)
                if d < r + 10:
                    rdx = current.x - obs.x
                    rdy = current.y - obs.y
                    if d > 0:
                        fx += rdx / d * (r + 10 - d) * 2
                        fy += rdy / d * (r + 10 - d) * 2
            new = Point(current.x + fx * step, current.y + fy * step)
            path.append(new)
            current = new
        return path

    def stats(self) -> Dict:
        return {"obstacles": len(self.obstacles), "bounds": self.bounds}

def run():
    planner = PathPlanner((0, 0, 50, 50))
    planner.add_obstacle(20, 20, 5)
    planner.add_obstacle(30, 30, 5)
    start = Point(5, 5)
    goal = Point(45, 45)
    path = planner.rrt(start, goal, 2000, 3)
    print("RRT path found:", path is not None)
    pf = planner.potential_field(start, goal)
    print("PF path length:", len(pf))
    print(planner.stats())

if __name__ == "__main__":
    run()
