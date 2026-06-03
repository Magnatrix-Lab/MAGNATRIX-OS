"""Phylogenetic Tree - Distance-based tree for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

@dataclass
class PhylogeneticTree:
    labels: List[str] = field(default_factory=list)
    distances: Dict[Tuple[str,str], float] = field(default_factory=dict)

    def add_distance(self, a: str, b: str, dist: float) -> None:
        self.distances[(a,b)] = dist
        self.distances[(b,a)] = dist

    def neighbor_joining(self) -> List[Tuple[str, str, float]]:
        nodes = self.labels[:]
        edges = []
        while len(nodes) > 1:
            if len(nodes) == 2:
                edges.append((nodes[0], nodes[1], self.distances.get((nodes[0], nodes[1]), 0)))
                break
            r = {n: sum(self.distances.get((n, m), 0) for m in nodes if m != n) for n in nodes}
            min_q = float('inf'); pair = None
            for i in range(len(nodes)):
                for j in range(i+1, len(nodes)):
                    q = (len(nodes)-2)*self.distances.get((nodes[i],nodes[j]),0) - r[nodes[i]] - r[nodes[j]]
                    if q < min_q: min_q = q; pair = (nodes[i], nodes[j])
            if pair:
                edges.append((pair[0], pair[1], self.distances.get(pair, 0)))
                nodes = [n for n in nodes if n not in pair]
                new_node = f"node_{len(edges)}"
                nodes.append(new_node)
        return edges

    def stats(self) -> dict:
        return {"species": len(self.labels), "distances": len(self.distances)}

def run():
    pt = PhylogeneticTree(["A", "B", "C"])
    pt.add_distance("A", "B", 1.0); pt.add_distance("B", "C", 2.0); pt.add_distance("A", "C", 3.0)
    edges = pt.neighbor_joining()
    print("Edges:", edges)
    print("Stats:", pt.stats())

if __name__ == "__main__": run()
