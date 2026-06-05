"""Social Graph — adjacency, centrality, clustering, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

@dataclass
class SocialGraph:
    nodes: Set[int] = field(default_factory=set)
    edges: List[Tuple[int, int]] = field(default_factory=list)
    weights: Dict[Tuple[int, int], float] = field(default_factory=dict)

    def add_edge(self, u: int, v: int, w: float = 1.0):
        self.nodes.add(u); self.nodes.add(v)
        self.edges.append((u, v))
        self.edges.append((v, u))
        self.weights[(u, v)] = w; self.weights[(v, u)] = w

    def degree(self, node: int) -> int:
        return sum(1 for u, v in self.edges if u == node)

    def degree_centrality(self) -> Dict[int, float]:
        n = len(self.nodes) - 1
        return {node: self.degree(node) / n if n > 0 else 0 for node in self.nodes}

    def clustering_coefficient(self, node: int) -> float:
        neighbors = [v for u, v in self.edges if u == node]
        if len(neighbors) < 2:
            return 0.0
        links = 0
        for i in range(len(neighbors)):
            for j in range(i+1, len(neighbors)):
                if (neighbors[i], neighbors[j]) in self.weights or (neighbors[j], neighbors[i]) in self.weights:
                    links += 1
        return 2 * links / (len(neighbors) * (len(neighbors) - 1))

    def path_length(self, start: int, end: int) -> Optional[int]:
        if start == end:
            return 0
        visited = {start}
        queue = [(start, 0)]
        while queue:
            node, dist = queue.pop(0)
            for u, v in self.edges:
                if u == node and v not in visited:
                    if v == end:
                        return dist + 1
                    visited.add(v)
                    queue.append((v, dist + 1))
        return None

    def stats(self) -> Dict:
        return {"nodes": len(self.nodes), "edges": len(self.edges)//2}

def run():
    sg = SocialGraph()
    sg.add_edge(1, 2); sg.add_edge(2, 3); sg.add_edge(1, 3); sg.add_edge(3, 4)
    print("Degree 1:", sg.degree(1))
    print("CC 1:", sg.clustering_coefficient(1))
    print("Path 1->4:", sg.path_length(1, 4))
    print(sg.stats())

if __name__ == "__main__":
    run()
