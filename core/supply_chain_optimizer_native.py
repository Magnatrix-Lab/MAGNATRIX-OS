#!/usr/bin/env python3
"""Supply Chain Optimizer for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import heapq

@dataclass
class SupplyNode:
    node_id: str
    inventory: int = 0
    demand: int = 0
    capacity: int = 100
    def to_dict(self): return asdict(self)

class SupplyChainOptimizer:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.nodes: Dict[str, SupplyNode] = {}
        self.edges: Dict[str, List[tuple]] = {}
    def add_node(self, node: SupplyNode):
        self.nodes[node.node_id] = node
        self.edges[node.node_id] = []
    def add_edge(self, src: str, dst: str, cost: float):
        if src in self.edges:
            self.edges[src].append((dst, cost))
    def optimize(self, source: str, target: str) -> Dict[str, Any]:
        dist = {n: float('inf') for n in self.nodes}
        dist[source] = 0
        pq = [(0, source)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]: continue
            for v, w in self.edges.get(u, []):
                if d + w < dist[v]:
                    dist[v] = d + w
                    heapq.heappush(pq, (dist[v], v))
        return {"shortest_cost": dist.get(target, float('inf')), "nodes": len(self.nodes)}
    def to_dict(self): return {"nodes": len(self.nodes), "edges": sum(len(v) for v in self.edges.values())}
