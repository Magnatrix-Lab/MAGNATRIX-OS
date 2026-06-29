
"""
knowledge_graph_builder_native.py
MAGNATRIX-OS Knowledge Graph Builder

Build knowledge graph nodes and edges from triplets. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class GraphNode:
    node_id: str
    label: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    degree: int = 0


@dataclass
class GraphEdge:
    edge_id: str
    source: str
    target: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraphBuilder:
    """Build knowledge graph nodes and edges from triplets."""

    def __init__(self, cache_dir: str = "./knowledge_graph"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self._load()

    def _load(self) -> None:
        nodes_file = self.cache_dir / "nodes.json"
        if nodes_file.exists():
            try:
                with open(nodes_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for nid, nd in data.items():
                        self.nodes[nid] = GraphNode(**nd)
            except Exception:
                pass
        edges_file = self.cache_dir / "edges.json"
        if edges_file.exists():
            try:
                with open(edges_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for eid, ed in data.items():
                        self.edges[eid] = GraphEdge(**ed)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "nodes.json", "w", encoding="utf-8") as f:
            json.dump({nid: {"node_id": n.node_id, "label": n.label, "entity_type": n.entity_type, "properties": n.properties, "degree": n.degree} for nid, n in self.nodes.items()}, f, indent=2)
        with open(self.cache_dir / "edges.json", "w", encoding="utf-8") as f:
            json.dump({eid: {"edge_id": e.edge_id, "source": e.source, "target": e.target, "label": e.label, "properties": e.properties} for eid, e in self.edges.items()}, f, indent=2)

    def add_triple(self, subject: str, predicate: str, object: str, confidence: float = 1.0) -> None:
        for entity, entity_type in [(subject, "subject"), (object, "object")]:
            if entity not in self.nodes:
                self.nodes[entity] = GraphNode(node_id=entity, label=entity, entity_type=entity_type)
            self.nodes[entity].degree += 1
        edge_id = f"{subject}_{predicate}_{object}"
        self.edges[edge_id] = GraphEdge(edge_id=edge_id, source=subject, target=object, label=predicate, properties={"confidence": confidence})
        self._save()

    def build_from_triples(self, triples) -> Dict[str, Any]:
        for t in triples:
            conf = getattr(t, "confidence", 1.0)
            self.add_triple(t.subject, t.predicate, t.object, conf)
        return self.get_stats()

    def get_neighbors(self, node_id: str) -> List[str]:
        neighbors = []
        for e in self.edges.values():
            if e.source == node_id:
                neighbors.append(e.target)
            elif e.target == node_id:
                neighbors.append(e.source)
        return neighbors

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = len(self.nodes)
        total_edges = len(self.edges)
        avg_degree = sum(n.degree for n in self.nodes.values()) / max(1, total_nodes)
        return {"nodes": total_nodes, "edges": total_edges, "avg_degree": round(avg_degree, 2)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["KnowledgeGraphBuilder", "GraphNode", "GraphEdge"]
