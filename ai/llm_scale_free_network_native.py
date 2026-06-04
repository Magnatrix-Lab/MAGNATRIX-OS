"""Scale Free Network - Barabasi-Albert model for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum, auto
import random
import math
from collections import Counter

@dataclass
class ScaleFreeNetwork:
    n: int = 20
    m: int = 2
    edges: Dict[str, List[str]] = field(default_factory=dict)

    def generate(self, seed: int = 42) -> Dict[str, List[str]]:
        random.seed(seed)
        nodes = [str(i) for i in range(self.m + 1)]
        edges = {node: [other for other in nodes if other != node] for node in nodes}
        for i in range(self.m + 1, self.n):
            new_node = str(i)
            all_edges = []
            for node, neighbors in edges.items():
                for neighbor in neighbors:
                    all_edges.append((node, neighbor))
            targets = set()
            while len(targets) < self.m:
                if all_edges:
                    edge = random.choice(all_edges)
                    targets.add(random.choice([edge[0], edge[1]]))
                else:
                    targets.add(random.choice(list(edges.keys())))
            edges[new_node] = list(targets)
            for target in targets:
                edges[target].append(new_node)
        self.edges = edges
        return edges

    def degree_distribution(self) -> Dict[int, int]:
        degrees = Counter(len(neighbors) for neighbors in self.edges.values())
        return dict(degrees)

    def stats(self) -> dict:
        return {"n": self.n, "m": self.m, "max_degree": max(len(v) for v in self.edges.values()) if self.edges else 0}

def run():
    sf = ScaleFreeNetwork(15, 2)
    sf.generate(42)
    print("Degree distribution:", sf.degree_distribution())
    print("Stats:", sf.stats())

if __name__ == "__main__": run()
