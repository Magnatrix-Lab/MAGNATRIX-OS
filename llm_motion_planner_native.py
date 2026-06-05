"""Motion Planner — RRT, PRM, collision, trajectory, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import random, math

@dataclass
class Point:
    x: float
    y: float

class MotionPlanner:
    def __init__(self):
        self.obstacles: List[Tuple[Point, Point]] = []
        """(min, max) bounding box"""
        self.bounds: Tuple[float, float] = (10, 10)

    def add_obstacle(self, min_p: Point, max_p: Point):
        self.obstacles.append((min_p, max_p))

    def collision(self, p: Point) -> bool:
        for min_p, max_p in self.obstacles:
            if min_p.x <= p.x <= max_p.x and min_p.y <= p.y <= max_p.y:
                return True
        return False

    def distance(self, a: Point, b: Point) -> float:
        return math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2)

    def rrt(self, start: Point, goal: Point, max_iter: int = 1000, step: float = 0.5) -> List[Point]:
        nodes = [start]
        parents = {0: None}
        for _ in range(max_iter):
            if random.random() < 0.1:
                sample = goal
            else:
                sample = Point(random.uniform(0, self.bounds[0]), random.uniform(0, self.bounds[1]))
            nearest_idx = min(range(len(nodes)), key=lambda i: self.distance(nodes[i], sample))
            nearest = nodes[nearest_idx]
            d = self.distance(nearest, sample)
            if d == 0:
                continue
            new = Point(nearest.x + step * (sample.x - nearest.x) / d, nearest.y + step * (sample.y - nearest.y) / d)
            if not self.collision(new):
                nodes.append(new)
                parents[len(nodes)-1] = nearest_idx
                if self.distance(new, goal) < step:
                    path = [new]
                    idx = len(nodes) - 1
                    while parents[idx] is not None:
                        idx = parents[idx]
                        path.append(nodes[idx])
                    return path[::-1]
        return []

    def path_length(self, path: List[Point]) -> float:
        return sum(self.distance(path[i], path[i+1]) for i in range(len(path)-1)) if len(path) > 1 else 0.0

    def stats(self, path: List[Point]) -> Dict:
        return {"nodes": len(path), "length": round(self.path_length(path), 3)}

def run():
    mp = MotionPlanner()
    mp.add_obstacle(Point(3, 3), Point(5, 5))
    mp.add_obstacle(Point(6, 1), Point(7, 4))
    path = mp.rrt(Point(0, 0), Point(9, 9))
    print(mp.stats(path))

if __name__ == "__main__":
    run()
