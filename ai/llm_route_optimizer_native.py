"""Route Optimizer - Shortest path for routes for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto
import math
import heapq

@dataclass
class RouteOptimizer:
    nodes: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    edges: Dict[str, List[Tuple[str, float]]] = field(default_factory=dict)
    
    def add_node(self, id: str, lat: float, lon: float) -> None:
        self.nodes[id] = (lat, lon)
    
    def add_edge(self, a: str, b: str, weight: Optional[float] = None) -> None:
        if weight is None:
            lat1, lon1 = self.nodes.get(a, (0, 0))
            lat2, lon2 = self.nodes.get(b, (0, 0))
            weight = math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)
        if a not in self.edges: self.edges[a] = []
        if b not in self.edges: self.edges[b] = []
        self.edges[a].append((b, weight))
        self.edges[b].append((a, weight))
    
    def shortest_path(self, start: str, end: str) -> Tuple[List[str], float]:
        dist = {n: float('inf') for n in self.nodes}
        dist[start] = 0
        prev = {}
        pq = [(0, start)]
        while pq:
            d, node = heapq.heappop(pq)
            if node == end: break
            for neighbor, weight in self.edges.get(node, []):
                nd = d + weight
                if nd < dist[neighbor]:
                    dist[neighbor] = nd
                    prev[neighbor] = node
                    heapq.heappush(pq, (nd, neighbor))
        if end not in prev and start != end: return [], float('inf')
        path = []
        node = end
        while node in prev:
            path.append(node)
            node = prev[node]
        path.append(start)
        return path[::-1], dist[end]
    
    def stats(self, start: str, end: str) -> dict:
        path, dist = self.shortest_path(start, end)
        return {"path_length": len(path), "distance": round(dist, 4), "nodes": len(self.nodes)}

def run():
    ro = RouteOptimizer()
    ro.add_node("A", 0, 0); ro.add_node("B", 1, 0); ro.add_node("C", 1, 1); ro.add_node("D", 2, 1)
    ro.add_edge("A", "B"); ro.add_edge("B", "C"); ro.add_edge("C", "D"); ro.add_edge("A", "C", 2.0)
    path, dist = ro.shortest_path("A", "D")
    print(f"Path: {path}, Distance: {dist:.4f}")
    print("Stats:", ro.stats("A", "D"))

if __name__ == "__main__": run()
