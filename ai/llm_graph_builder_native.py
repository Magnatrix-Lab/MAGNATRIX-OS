"""Graph Builder - Graph construction for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum, auto

class GraphType(Enum):
    DIRECTED = auto()
    UNDIRECTED = auto()
    WEIGHTED = auto()

@dataclass
class GraphBuilder:
    graph_type: GraphType = GraphType.UNDIRECTED
    nodes: Set[str] = field(default_factory=set)
    edges: Dict[str, List[Tuple[str, Optional[float]]]] = field(default_factory=dict)

    def add_node(self, node: str) -> None:
        self.nodes.add(node)
        if node not in self.edges:
            self.edges[node] = []

    def add_edge(self, a: str, b: str, weight: Optional[float] = None) -> None:
        self.add_node(a)
        self.add_node(b)
        self.edges[a].append((b, weight))
        if self.graph_type == GraphType.UNDIRECTED:
            self.edges[b].append((a, weight))

    def neighbors(self, node: str) -> List[str]:
        return [n for n, _ in self.edges.get(node, [])]

    def degree(self, node: str) -> int:
        return len(self.edges.get(node, []))

    def stats(self) -> dict:
        return {"type": self.graph_type.name, "nodes": len(self.nodes), "edges": sum(len(v) for v in self.edges.values()) // (1 if self.graph_type == GraphType.DIRECTED else 2)}

def run():
    gb = GraphBuilder(GraphType.UNDIRECTED)
    gb.add_edge("A", "B", 1.0)
    gb.add_edge("B", "C", 2.0)
    gb.add_edge("C", "A", 3.0)
    print("Neighbors of A:", gb.neighbors("A"))
    print("Degree of B:", gb.degree("B"))
    print("Stats:", gb.stats())

if __name__ == "__main__":
    run()
