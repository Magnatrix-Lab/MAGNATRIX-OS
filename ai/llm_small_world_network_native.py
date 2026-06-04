"""Small World Network - Watts-Strogatz model for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum, auto
import random
import math

@dataclass
class SmallWorldNetwork:
    n: int = 20
    k: int = 4
    p: float = 0.3
    edges: Dict[str, List[str]] = field(default_factory=dict)

    def generate(self, seed: int = 42) -> Dict[str, List[str]]:
        random.seed(seed)
        nodes = [str(i) for i in range(self.n)]
        edges = {node: [] for node in nodes}
        for i in range(self.n):
            for j in range(1, self.k // 2 + 1):
                neighbor = nodes[(i + j) % self.n]
                edges[nodes[i]].append(neighbor)
                edges[neighbor].append(nodes[i])
        for i in range(self.n):
            for j in range(1, self.k // 2 + 1):
                if random.random() < self.p:
                    old_neighbor = nodes[(i + j) % self.n]
                    new_neighbor = random.choice(nodes)
                    if new_neighbor != nodes[i] and new_neighbor != old_neighbor:
                        edges[nodes[i]].remove(old_neighbor)
                        edges[old_neighbor].remove(nodes[i])
                        edges[nodes[i]].append(new_neighbor)
                        edges[new_neighbor].append(nodes[i])
        self.edges = edges
        return edges

    def clustering_coefficient(self) -> float:
        if not self.edges: return 0
        total = 0
        for node, neighbors in self.edges.items():
            if len(neighbors) < 2: continue
            links = 0
            for i in range(len(neighbors)):
                for j in range(i+1, len(neighbors)):
                    if neighbors[j] in self.edges.get(neighbors[i], []):
                        links += 1
            possible = len(neighbors) * (len(neighbors) - 1) // 2
            if possible > 0:
                total += links / possible
        return total / len(self.edges)

    def stats(self) -> dict:
        return {"n": self.n, "k": self.k, "p": self.p, "clustering": round(self.clustering_coefficient(), 4)}

def run():
    sw = SmallWorldNetwork(10, 4, 0.3)
    sw.generate(42)
    print("Clustering:", round(sw.clustering_coefficient(), 4))
    print("Stats:", sw.stats())

if __name__ == "__main__": run()
