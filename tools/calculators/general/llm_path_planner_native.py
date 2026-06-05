"""Path Planner — A*, RRT, grid-based, collision-free, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import heapq

@dataclass
class PathPlanner:
    grid: List[List[int]] = field(default_factory=list)
    """0 = free, 1 = obstacle"""

    def astar(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        if not self.grid or not (0 <= start[0] < len(self.grid) and 0 <= start[1] < len(self.grid[0])):
            return []
        open_set = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        while open_set:
            _, current = heapq.heappop(open_set)
            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                return path[::-1]
            for dx, dy in [(0,1),(1,0),(0,-1),(-1,0)]:
                nxt = (current[0]+dx, current[1]+dy)
                if 0 <= nxt[0] < len(self.grid) and 0 <= nxt[1] < len(self.grid[0]) and self.grid[nxt[0]][nxt[1]] == 0:
                    ng = g_score[current] + 1
                    if ng < g_score.get(nxt, float('inf')):
                        came_from[nxt] = current
                        g_score[nxt] = ng
                        h = abs(nxt[0]-goal[0]) + abs(nxt[1]-goal[1])
                        heapq.heappush(open_set, (ng + h, nxt))
        return []

    def rrt(self, start: Tuple[float, float], goal: Tuple[float, float], max_iter: int = 1000, step: float = 0.5) -> List[Tuple[float, float]]:
        import random
        nodes = [start]
        parents = {start: None}
        for _ in range(max_iter):
            if random.random() < 0.1:
                sample = goal
            else:
                sample = (random.uniform(0, 10), random.uniform(0, 10))
            nearest = min(nodes, key=lambda n: (n[0]-sample[0])**2 + (n[1]-sample[1])**2)
            dx, dy = sample[0]-nearest[0], sample[1]-nearest[1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist == 0:
                continue
            new = (nearest[0] + step * dx / dist, nearest[1] + step * dy / dist)
            nodes.append(new)
            parents[new] = nearest
            if (new[0]-goal[0])**2 + (new[1]-goal[1])**2 < step**2:
                path = [new]
                while parents[path[-1]] is not None:
                    path.append(parents[path[-1]])
                return path[::-1]
        return []

    def stats(self) -> Dict:
        return {"grid_size": f"{len(self.grid)}x{len(self.grid[0])}" if self.grid else "none"}

def run():
    planner = PathPlanner([[0,0,1,0],[0,0,1,0],[0,0,0,0],[0,1,0,0]])
    print("A*:", planner.astar((0,0), (3,3)))
    print("RRT:", planner.rrt((0,0), (9,9))[:5])
    print(planner.stats())

if __name__ == "__main__":
    run()
