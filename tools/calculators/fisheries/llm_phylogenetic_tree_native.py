"""Phylogenetic Tree — UPGMA, distance matrix, Newick format, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class PhyloNode:
    name: str
    children: List['PhyloNode'] = field(default_factory=list)
    height: float = 0.0

class PhylogeneticTree:
    def __init__(self, labels: List[str], distances: List[List[float]]):
        self.labels = labels
        self.distances = distances

    def upgma(self) -> PhyloNode:
        n = len(self.labels)
        nodes = [PhyloNode(name=self.labels[i]) for i in range(n)]
        cluster_size = [1] * n
        active = set(range(n))
        D = [row[:] for row in self.distances]
        while len(active) > 1:
            min_d = float('inf')
            pair = (0, 1)
            for i in active:
                for j in active:
                    if i < j and D[i][j] < min_d:
                        min_d = D[i][j]; pair = (i, j)
            i, j = pair
            new_node = PhyloNode(name=f"Node_{i}_{j}", children=[nodes[i], nodes[j]], height=min_d/2)
            nodes.append(new_node)
            cluster_size.append(cluster_size[i] + cluster_size[j])
            active.remove(i); active.remove(j)
            idx = len(nodes) - 1
            for k in active:
                d = (D[i][k] * cluster_size[i] + D[j][k] * cluster_size[j]) / (cluster_size[i] + cluster_size[j])
                D[idx][k] = d; D[k][idx] = d
            active.add(idx)
        return nodes[-1]

    def to_newick(self, node: PhyloNode) -> str:
        if not node.children:
            return node.name
        children = [self.to_newick(c) for c in node.children]
        return f"({','.join(children)}){node.name}"

    def stats(self, root: PhyloNode) -> Dict:
        def count(n): return 1 + sum(count(c) for c in n.children)
        return {"leaves": count(root), "root": root.name}

def run():
    labels = ["A", "B", "C", "D"]
    dist = [[0,2,4,6],[2,0,4,6],[4,4,0,2],[6,6,2,0]]
    tree = PhylogeneticTree(labels, dist)
    root = tree.upgma()
    print("Newick:", tree.to_newick(root))
    print(tree.stats(root))

if __name__ == "__main__":
    run()
