"""Network Topology — mesh, star, ring, spanning tree, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto

class TopologyType(Enum):
    MESH = auto(); STAR = auto(); RING = auto(); BUS = auto(); TREE = auto()

@dataclass
class NetworkTopology:
    nodes: Set[str] = field(default_factory=set)
    edges: List[Tuple[str, str]] = field(default_factory=list)

    def add_node(self, n: str):
        self.nodes.add(n)

    def add_edge(self, a: str, b: str):
        self.edges.append((a, b))
        self.edges.append((b, a))

    def degree(self, node: str) -> int:
        return sum(1 for a, b in self.edges if a == node)

    def detect_topology(self) -> TopologyType:
        n = len(self.nodes)
        if n == 0:
            return TopologyType.BUS
        edge_count = len(self.edges) // 2
        if edge_count == n * (n - 1) // 2:
            return TopologyType.MESH
        center = [node for node in self.nodes if self.degree(node) == n - 1]
        if center and edge_count == n - 1:
            return TopologyType.STAR
        if all(self.degree(node) == 2 for node in self.nodes) and edge_count == n:
            return TopologyType.RING
        if edge_count == n - 1:
            return TopologyType.TREE
        return TopologyType.BUS

    def spanning_tree(self) -> List[Tuple[str, str]]:
        if not self.nodes:
            return []
        visited = {next(iter(self.nodes))}
        tree = []
        while len(visited) < len(self.nodes):
            for a, b in self.edges:
                if a in visited and b not in visited:
                    visited.add(b)
                    tree.append((a, b))
                    break
        return tree

    def redundancy(self) -> float:
        n = len(self.nodes)
        if n < 2:
            return 0.0
        min_edges = n - 1
        actual = len(self.edges) // 2
        return (actual - min_edges) / min_edges if min_edges > 0 else 0.0

    def stats(self) -> Dict:
        return {"nodes": len(self.nodes), "edges": len(self.edges)//2, "topology": self.detect_topology().name, "redundancy": round(self.redundancy(), 2)}

def run():
    nt = NetworkTopology()
    for i in range(5):
        nt.add_node(f"N{i}")
    nt.add_edge("N0", "N1")
    nt.add_edge("N0", "N2")
    nt.add_edge("N0", "N3")
    nt.add_edge("N0", "N4")
    print(nt.stats())
    print("Spanning tree:", nt.spanning_tree())

if __name__ == "__main__":
    run()
