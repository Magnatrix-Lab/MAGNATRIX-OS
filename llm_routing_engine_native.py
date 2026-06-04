"""Routing Engine — shortest path, A*, Dijkstra, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import math
import heapq

@dataclass
class RouteNode:
    node_id: str
    lat: float = 0.0
    lon: float = 0.0

class RoutingEngine:
    def __init__(self):
        self.nodes: Dict[str, RouteNode] = {}
        self.edges: Dict[str, List[Tuple[str, float]]] = {}
        self.graph: Dict[str, Dict[str, float]] = {}

    def add_node(self, node_id: str, lat: float = 0.0, lon: float = 0.0):
        self.nodes[node_id] = RouteNode(node_id, lat, lon)
        if node_id not in self.edges:
            self.edges[node_id] = []
        if node_id not in self.graph:
            self.graph[node_id] = {}

    def add_edge(self, from_id: str, to_id: str, weight: float):
        if from_id not in self.edges:
            self.edges[from_id] = []
        self.edges[from_id].append((to_id, weight))
        self.graph[from_id][to_id] = weight

    def add_bidirectional_edge(self, a: str, b: str, weight: float):
        self.add_edge(a, b, weight)
        self.add_edge(b, a, weight)

    def dijkstra(self, start: str, end: str) -> Optional[Tuple[List[str], float]]:
        dist = {n: float('inf') for n in self.nodes}
        prev = {}
        dist[start] = 0
        pq = [(0, start)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == end:
                break
            for v, w in self.edges.get(u, []):
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    prev[v] = u
                    heapq.heappush(pq, (dist[v], v))
        if end not in prev and start != end:
            return None
        path = []
        at = end
        while at != start:
            path.append(at)
            at = prev.get(at, start)
            if at == end:
                return None
        path.append(start)
        return list(reversed(path)), dist[end]

    def astar(self, start: str, end: str) -> Optional[Tuple[List[str], float]]:
        def heuristic(node: str) -> float:
            a = self.nodes.get(node, RouteNode("", 0, 0))
            b = self.nodes.get(end, RouteNode("", 0, 0))
            return math.sqrt((a.lat - b.lat) ** 2 + (a.lon - b.lon) ** 2)
        g = {n: float('inf') for n in self.nodes}
        f = {n: float('inf') for n in self.nodes}
        prev = {}
        g[start] = 0
        f[start] = heuristic(start)
        open_set = [(f[start], start)]
        closed = set()
        while open_set:
            _, u = heapq.heappop(open_set)
            if u in closed:
                continue
            closed.add(u)
            if u == end:
                break
            for v, w in self.edges.get(u, []):
                if v in closed:
                    continue
                tentative = g[u] + w
                if tentative < g[v]:
                    prev[v] = u
                    g[v] = tentative
                    f[v] = g[v] + heuristic(v)
                    heapq.heappush(open_set, (f[v], v))
        if end not in prev and start != end:
            return None
        path = []
        at = end
        while at != start:
            path.append(at)
            at = prev.get(at, start)
            if at == end:
                return None
        path.append(start)
        return list(reversed(path)), g[end]

    def stats(self) -> Dict:
        return {"nodes": len(self.nodes), "edges": sum(len(v) for v in self.edges.values())}

def run():
    router = RoutingEngine()
    for i in range(6):
        router.add_node(f"n{i}")
    router.add_bidirectional_edge("n0", "n1", 4)
    router.add_bidirectional_edge("n0", "n2", 2)
    router.add_bidirectional_edge("n1", "n3", 5)
    router.add_bidirectional_edge("n2", "n3", 1)
    router.add_bidirectional_edge("n3", "n4", 3)
    router.add_bidirectional_edge("n4", "n5", 2)
    print("Dijkstra:", router.dijkstra("n0", "n5"))
    print(router.stats())

if __name__ == "__main__":
    run()
