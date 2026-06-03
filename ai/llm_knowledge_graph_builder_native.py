"""LLM Knowledge Graph Builder — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class RelationType(Enum):
    IS_A = auto()
    HAS_A = auto()
    PART_OF = auto()
    RELATED_TO = auto()
    CAUSES = auto()
    FOLLOWS = auto()

@dataclass
class KnowledgeNode:
    id: str
    label: str
    entity_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class KnowledgeEdge:
    id: str
    source: str
    target: str
    relation: RelationType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class KnowledgeGraphBuilder:
    def __init__(self) -> None:
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: Dict[str, KnowledgeEdge] = {}
        self._adjacency: Dict[str, List[str]] = {}

    def add_node(self, node: KnowledgeNode) -> None:
        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []

    def add_edge(self, edge: KnowledgeEdge) -> None:
        self._edges[edge.id] = edge
        if edge.source not in self._adjacency:
            self._adjacency[edge.source] = []
        self._adjacency[edge.source].append(edge.id)

    def get_neighbors(self, node_id: str) -> List[KnowledgeNode]:
        edge_ids = self._adjacency.get(node_id, [])
        neighbors = []
        for eid in edge_ids:
            edge = self._edges.get(eid)
            if edge and edge.target in self._nodes:
                neighbors.append(self._nodes[edge.target])
        return neighbors

    def find_path(self, start: str, end: str) -> List[str]:
        visited = set()
        queue = [(start, [start])]
        while queue:
            current, path = queue.pop(0)
            if current == end:
                return path
            visited.add(current)
            for eid in self._adjacency.get(current, []):
                edge = self._edges.get(eid)
                if edge and edge.target not in visited:
                    queue.append((edge.target, path + [edge.target]))
        return []

    def get_stats(self) -> Dict[str, Any]:
        return {"nodes": len(self._nodes), "edges": len(self._edges), "density": len(self._edges) / (len(self._nodes) * (len(self._nodes) - 1)) if len(self._nodes) > 1 else 0.0}

def run() -> None:
    print("Knowledge Graph Builder test")
    e = KnowledgeGraphBuilder()
    e.add_node(KnowledgeNode("n1", "Paris", "city"))
    e.add_node(KnowledgeNode("n2", "France", "country"))
    e.add_node(KnowledgeNode("n3", "Eiffel Tower", "landmark"))
    e.add_edge(KnowledgeEdge("e1", "n1", "n2", RelationType.PART_OF))
    e.add_edge(KnowledgeEdge("e2", "n3", "n1", RelationType.PART_OF))
    print("  Neighbors of n1: " + str([n.label for n in e.get_neighbors("n1")]))
    print("  Path n3 to n2: " + str(e.find_path("n3", "n2")))
    print("  Stats: " + str(e.get_stats()))
    print("Knowledge Graph Builder test complete.")

if __name__ == "__main__":
    run()
