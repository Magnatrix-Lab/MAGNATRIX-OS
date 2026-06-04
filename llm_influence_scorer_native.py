"""Influence Scorer — PageRank, eigenvector, HITS, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class InfluenceScorer:
    nodes: List[int] = field(default_factory=list)
    edges: List[Tuple[int, int]] = field(default_factory=list)

    def pagerank(self, damping: float = 0.85, iterations: int = 100) -> Dict[int, float]:
        n = len(self.nodes)
        if n == 0:
            return {}
        pr = {node: 1.0 / n for node in self.nodes}
        out_deg = {node: sum(1 for u, v in self.edges if u == node) for node in self.nodes}
        for _ in range(iterations):
            new_pr = {}
            for node in self.nodes:
                s = sum(pr[u] / out_deg[u] for u, v in self.edges if v == node and out_deg[u] > 0)
                new_pr[node] = (1 - damping) / n + damping * s
            pr = new_pr
        return pr

    def hits(self, iterations: int = 50) -> Tuple[Dict[int, float], Dict[int, float]]:
        auth = {node: 1.0 for node in self.nodes}
        hub = {node: 1.0 for node in self.nodes}
        for _ in range(iterations):
            new_auth = {node: sum(hub[u] for u, v in self.edges if v == node) for node in self.nodes}
            new_hub = {node: sum(auth[v] for u, v in self.edges if u == node) for node in self.nodes}
            a_norm = max(new_auth.values()) if new_auth else 1
            h_norm = max(new_hub.values()) if new_hub else 1
            auth = {k: v / a_norm for k, v in new_auth.items()}
            hub = {k: v / h_norm for k, v in new_hub.items()}
        return auth, hub

    def stats(self) -> Dict:
        return {"nodes": len(self.nodes), "edges": len(self.edges)}

def run():
    isr = InfluenceScorer([1,2,3,4], [(1,2),(2,3),(3,1),(3,4)])
    print("PageRank:", isr.pagerank())
    auth, hub = isr.hits()
    print("HITS auth:", auth)
    print(isr.stats())

if __name__ == "__main__":
    run()
