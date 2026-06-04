"""Community Detector — Louvain, modularity, label propagation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import random

@dataclass
class CommunityDetector:
    edges: List[Tuple[int, int]] = field(default_factory=list)
    nodes: Set[int] = field(default_factory=set)

    def modularity(self, communities: Dict[int, int]) -> float:
        m = len(self.edges) // 2
        if m == 0:
            return 0.0
        q = 0.0
        for node in self.nodes:
            for other in self.nodes:
                if communities.get(node) == communities.get(other):
                    aij = 1 if (node, other) in self.edges or (other, node) in self.edges else 0
                    ki = sum(1 for u, v in self.edges if u == node)
                    kj = sum(1 for u, v in self.edges if u == other)
                    q += (aij - ki * kj / (2 * m)) / (2 * m)
        return q

    def label_propagation(self, iterations: int = 50) -> Dict[int, int]:
        labels = {node: node for node in self.nodes}
        for _ in range(iterations):
            nodes = list(self.nodes)
            random.shuffle(nodes)
            for node in nodes:
                neighbor_labels = [labels[v] for u, v in self.edges if u == node]
                if neighbor_labels:
                    labels[node] = max(set(neighbor_labels), key=neighbor_labels.count)
        return labels

    def stats(self, communities: Dict[int, int]) -> Dict:
        comms = {}
        for node, c in communities.items():
            comms[c] = comms.get(c, []) + [node]
        return {"communities": len(comms), "modularity": self.modularity(communities), "sizes": [len(v) for v in comms.values()]}

def run():
    cd = CommunityDetector()
    for i in range(10):
        cd.nodes.add(i)
    edges = [(0,1),(1,2),(2,0),(3,4),(4,5),(5,3),(0,3),(2,5)]
    for e in edges:
        cd.edges.append(e); cd.edges.append((e[1], e[0]))
    comms = cd.label_propagation()
    print(cd.stats(comms))

if __name__ == "__main__":
    run()
