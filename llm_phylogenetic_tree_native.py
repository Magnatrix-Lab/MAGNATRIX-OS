"""Phylogenetic Tree — UPGMA, distance matrix, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class PhyloNode:
    name: str
    height: float = 0.0
    children: List["PhyloNode"] = field(default_factory=list)
    distance: float = 0.0

class PhylogeneticTree:
    def __init__(self):
        self.labels: List[str] = []
        self.matrix: List[List[float]] = []
        self.root: Optional[PhyloNode] = None

    def set_distance_matrix(self, labels: List[str], matrix: List[List[float]]):
        self.labels = labels
        self.matrix = [row[:] for row in matrix]

    def upgma(self) -> PhyloNode:
        n = len(self.labels)
        nodes = [PhyloNode(name) for name in self.labels]
        sizes = [1] * n
        active = list(range(n))
        dist = [row[:] for row in self.matrix]
        while len(active) > 1:
            min_dist = float('inf')
            min_i, min_j = 0, 1
            for i in range(len(active)):
                for j in range(i+1, len(active)):
                    a, b = active[i], active[j]
                    if dist[a][b] < min_dist:
                        min_dist = dist[a][b]
                        min_i, min_j = i, j
            a, b = active[min_i], active[min_j]
            new_height = dist[a][b] / 2
            new_node = PhyloNode(f"Node_{a}_{b}", new_height, [nodes[a], nodes[b]], dist[a][b])
            nodes.append(new_node)
            sizes.append(sizes[a] + sizes[b])
            active.append(len(nodes) - 1)
            # Update distances
            new_dist = [0.0] * len(dist)
            for k in active[:-1]:
                d = (dist[a][k] * sizes[a] + dist[b][k] * sizes[b]) / (sizes[a] + sizes[b])
                new_dist[k] = d
            new_row = new_dist[:]
            new_row.append(0.0)
            for row in dist:
                row.append(0.0)
            dist.append(new_row)
            active = [x for idx, x in enumerate(active) if idx not in (min_i, min_j)]
        self.root = nodes[active[0]]
        return self.root

    def newick(self, node: PhyloNode = None) -> str:
        node = node or self.root
        if not node.children:
            return node.name
        children_str = ",".join(self.newick(c) for c in node.children)
        return f"({children_str}):{node.distance:.3f}"

    def stats(self) -> Dict:
        return {"labels": len(self.labels), "root": self.root.name if self.root else None}

def run():
    tree = PhylogeneticTree()
    labels = ["A", "B", "C", "D"]
    matrix = [[0, 2, 4, 4], [2, 0, 4, 4], [4, 4, 0, 2], [4, 4, 2, 0]]
    tree.set_distance_matrix(labels, matrix)
    tree.upgma()
    print(tree.newick())
    print(tree.stats())

if __name__ == "__main__":
    run()
