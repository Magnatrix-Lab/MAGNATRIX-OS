"""Community Detection Advanced - Louvain for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum, auto
from collections import defaultdict
import math

@dataclass
class CommunityDetectionAdvanced:

    def modularity(self, edges: Dict[str, List[str]], communities: Dict[str, int]) -> float:
        m = sum(len(neighbors) for neighbors in edges.values()) / 2
        if m == 0: return 0
        q = 0
        for node, neighbors in edges.items():
            ki = len(neighbors)
            for neighbor in neighbors:
                if communities.get(node) == communities.get(neighbor):
                    kj = len(edges.get(neighbor, []))
                    q += 1 - (ki * kj) / (2 * m)
        return q / (2 * m)

    def louvain(self, edges: Dict[str, List[str]], max_iter: int = 10) -> Dict[str, int]:
        communities = {node: i for i, node in enumerate(edges.keys())}
        for _ in range(max_iter):
            improved = False
            for node in edges:
                best_comm = communities[node]
                best_gain = 0
                neighbor_comms = defaultdict(int)
                for neighbor in edges[node]:
                    neighbor_comms[communities[neighbor]] += 1
                for comm, count in neighbor_comms.items():
                    if comm != communities[node]:
                        gain = count
                        if gain > best_gain:
                            best_gain = gain
                            best_comm = comm
                if best_comm != communities[node]:
                    communities[node] = best_comm
                    improved = True
            if not improved: break
        return communities

    def stats(self, edges: Dict[str, List[str]]) -> dict:
        communities = self.louvain(edges)
        return {"communities": len(set(communities.values())), "modularity": round(self.modularity(edges, communities), 4)}

def run():
    cda = CommunityDetectionAdvanced()
    edges = {"A": ["B", "C"], "B": ["A", "C"], "C": ["A", "B", "D"], "D": ["C", "E"], "E": ["D"]}
    communities = cda.louvain(edges)
    print("Communities:", communities)
    print("Stats:", cda.stats(edges))

if __name__ == "__main__": run()
