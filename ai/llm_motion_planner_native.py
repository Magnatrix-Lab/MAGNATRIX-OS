"""Motion Planner - Path planning for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Set
from collections import deque

@dataclass
class MotionPlanner:
    grid_size: int = 5
    obstacles: Set[Tuple[int,int]] = field(default_factory=set)

    def plan(self, start: Tuple[int,int], goal: Tuple[int,int]) -> List[Tuple[int,int]]:
        queue = deque([(start, [start])])
        visited = {start}
        while queue:
            pos, path = queue.popleft()
            if pos == goal: return path
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                np = (pos[0]+dx, pos[1]+dy)
                if 0<=np[0]<self.grid_size and 0<=np[1]<self.grid_size and np not in self.obstacles and np not in visited:
                    visited.add(np)
                    queue.append((np, path+[np]))
        return []

    def stats(self, start: Tuple[int,int], goal: Tuple[int,int]) -> dict:
        path = self.plan(start, goal)
        return {"path_len": len(path), "obstacles": len(self.obstacles)}

def run():
    mp = MotionPlanner(5)
    mp.obstacles = {(1,1),(1,2),(2,2)}
    path = mp.plan((0,0), (4,4))
    print("Path:", path)
    print("Stats:", mp.stats((0,0),(4,4)))

if __name__ == "__main__": run()
