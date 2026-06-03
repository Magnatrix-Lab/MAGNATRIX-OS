"""Path Finder - Graph path algorithms for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum, auto
import heapq

class PathAlgorithm(Enum):
    BFS = auto()
    DFS = auto()
    DIJKSTRA = auto()
    ASTAR = auto()

@dataclass
class PathFinder:
    algorithm: PathAlgorithm = PathAlgorithm.DIJKSTRA
    edges: Dict[str, List[Tuple[str, float]]] = field(default_factory=dict)

    def add_edge(self, a: str, b: str, weight: float = 1.0) -> None:
        if a not in self.edges: self.edges[a] = []
        self.edges[a].append((b, weight))

    def find_path(self, start: str, goal: str) -> List[str]:
        if self.algorithm == PathAlgorithm.BFS:
            return self._bfs(start, goal)
        if self.algorithm == PathAlgorithm.DFS:
            return self._dfs(start, goal, set(), [start])
        if self.algorithm == PathAlgorithm.DIJKSTRA:
            return self._dijkstra(start, goal)
        return []

    def _bfs(self, start: str, goal: str) -> List[str]:
        from collections import deque
        queue = deque([(start, [start])])
        visited = {start}
        while queue:
            node, path = queue.popleft()
            if node == goal: return path
            for neighbor, _ in self.edges.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []

    def _dfs(self, node: str, goal: str, visited: Set[str], path: List[str]) -> List[str]:
        if node == goal: return path
        visited.add(node)
        for neighbor, _ in self.edges.get(node, []):
            if neighbor not in visited:
                result = self._dfs(neighbor, goal, visited, path + [neighbor])
                if result: return result
        return []

    def _dijkstra(self, start: str, goal: str) -> List[str]:
        dist = {n: float('inf') for n in self.edges}
        dist[start] = 0
        prev = {}
        pq = [(0, start)]
        while pq:
            d, node = heapq.heappop(pq)
            if node == goal:
                path = []
                while node in prev:
                    path.append(node)
                    node = prev[node]
                path.append(start)
                return path[::-1]
            for neighbor, w in self.edges.get(node, []):
                nd = d + w
                if nd < dist.get(neighbor, float('inf')):
                    dist[neighbor] = nd
                    prev[neighbor] = node
                    heapq.heappush(pq, (nd, neighbor))
        return []

    def stats(self) -> dict:
        return {"algorithm": self.algorithm.name, "nodes": len(self.edges)}

def run():
    pf = PathFinder(PathAlgorithm.DIJKSTRA)
    for a, b, w in [("A","B",1),("B","C",2),("A","C",5),("C","D",1)]:
        pf.add_edge(a, b, w)
    print("Dijkstra A->D:", pf.find_path("A", "D"))
    print("BFS A->D:", PathFinder(PathAlgorithm.BFS, pf.edges).find_path("A", "D"))
    print("Stats:", pf.stats())

if __name__ == "__main__":
    run()
