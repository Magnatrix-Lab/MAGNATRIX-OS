"""Military Logistics Router — nodes, capacity, time, risk, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import heapq

@dataclass
class LogisticsRouter:
    nodes: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    edges: Dict[Tuple[str, str], Tuple[float, float]] = field(default_factory=dict)
    """(from, to) -> (time, risk)"""

    def add_node(self, name: str, x: float, y: float):
        self.nodes[name] = (x, y)

    def add_edge(self, a: str, b: str, time: float, risk: float = 0.0):
        self.edges[(a, b)] = (time, risk)

    def shortest_path(self, start: str, goal: str, weight: str = "time") -> Tuple[List[str], float]:
        dist = {start: 0.0}
        prev = {}
        open_set = [(0, start)]
        while open_set:
            d, current = heapq.heappop(open_set)
            if current == goal:
                path = [current]
                while current in prev:
                    current = prev[current]
                    path.append(current)
                return path[::-1], d
            for (a, b), (t, r) in self.edges.items():
                if a == current:
                    w = t if weight == "time" else r
                    nd = d + w
                    if b not in dist or nd < dist[b]:
                        dist[b] = nd
                        prev[b] = current
                        heapq.heappush(open_set, (nd, b))
        return [], float('inf')

    def capacity_check(self, route: List[str], max_risk: float = 5.0) -> bool:
        total_risk = 0.0
        for i in range(len(route) - 1):
            e = self.edges.get((route[i], route[i+1]))
            if e:
                total_risk += e[1]
        return total_risk <= max_risk

    def stats(self) -> Dict:
        return {"nodes": len(self.nodes), "edges": len(self.edges)}

def run():
    lr = LogisticsRouter()
    lr.add_node("Base", 0, 0)
    lr.add_node("FWD", 50, 0)
    lr.add_node("OBJ", 100, 20)
    lr.add_edge("Base", "FWD", 2, 1)
    lr.add_edge("FWD", "OBJ", 3, 2)
    path, cost = lr.shortest_path("Base", "OBJ")
    print("Path:", path, "cost:", cost)
    print(lr.stats())

if __name__ == "__main__":
    run()
