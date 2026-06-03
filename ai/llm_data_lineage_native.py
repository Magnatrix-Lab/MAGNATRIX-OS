"""
llm_data_lineage_native.py
MAGNATRIX-OS Data Lineage Engine
Native Python, stdlib only.
Provides data lineage tracking, provenance graph construction, impact analysis,
and upstream/downstream dependency mapping for datasets and models.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class LineageType(Enum):
    DATASET = "dataset"
    MODEL = "model"
    PIPELINE = "pipeline"
    TRANSFORMATION = "transformation"
    EXTERNAL = "external"


class LineageStatus(Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DELETED = "deleted"


@dataclass
class LineageNode:
    id: str
    name: str
    node_type: LineageType
    description: str
    created_at: float
    status: LineageStatus = LineageStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "node_type": self.node_type.value,
            "description": self.description, "created_at": self.created_at,
            "status": self.status.value, "metadata": self.metadata, "tags": self.tags,
        }


@dataclass
class LineageEdge:
    source_id: str
    target_id: str
    edge_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id, "target_id": self.target_id,
            "edge_type": self.edge_type, "metadata": self.metadata, "created_at": self.created_at,
        }


@dataclass
class ImpactReport:
    node_id: str
    upstream: List[str]
    downstream: List[str]
    total_affected: int
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id, "upstream": self.upstream,
            "downstream": self.downstream, "total_affected": self.total_affected,
            "generated_at": self.generated_at,
        }


class DataLineageEngine:
    """
    Data lineage tracking engine with provenance graph and impact analysis.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: List[LineageEdge] = []
        self._adjacency: Dict[str, List[str]] = {}  # source -> [targets]
        self._reverse: Dict[str, List[str]] = {}    # target -> [sources]

    def register_node(self, node: LineageNode) -> None:
        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []
        if node.id not in self._reverse:
            self._reverse[node.id] = []

    def add_edge(self, source_id: str, target_id: str, edge_type: str = "derived_from",
                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        if source_id not in self._nodes or target_id not in self._nodes:
            return False
        edge = LineageEdge(source_id=source_id, target_id=target_id, edge_type=edge_type, metadata=metadata or {})
        self._edges.append(edge)
        self._adjacency.setdefault(source_id, []).append(target_id)
        self._reverse.setdefault(target_id, []).append(source_id)
        return True

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        self._edges = [e for e in self._edges if e.source_id != node_id and e.target_id != node_id]
        self._adjacency.pop(node_id, None)
        self._reverse.pop(node_id, None)
        for k in self._adjacency:
            self._adjacency[k] = [v for v in self._adjacency[k] if v != node_id]
        for k in self._reverse:
            self._reverse[k] = [v for v in self._reverse[k] if v != node_id]
        return True

    def get_upstream(self, node_id: str, depth: int = -1) -> List[str]:
        visited: Set[str] = set()
        stack = [(node_id, 0)]
        while stack:
            current, d = stack.pop()
            if current in visited or current == node_id:
                continue
            if depth >= 0 and d > depth:
                continue
            visited.add(current)
            for parent in self._reverse.get(current, []):
                stack.append((parent, d + 1))
        return list(visited)

    def get_downstream(self, node_id: str, depth: int = -1) -> List[str]:
        visited: Set[str] = set()
        stack = [(node_id, 0)]
        while stack:
            current, d = stack.pop()
            if current in visited or current == node_id:
                continue
            if depth >= 0 and d > depth:
                continue
            visited.add(current)
            for child in self._adjacency.get(current, []):
                stack.append((child, d + 1))
        return list(visited)

    def impact_analysis(self, node_id: str) -> ImpactReport:
        upstream = self.get_upstream(node_id)
        downstream = self.get_downstream(node_id)
        return ImpactReport(
            node_id=node_id, upstream=upstream, downstream=downstream,
            total_affected=len(upstream) + len(downstream)
        )

    def get_lineage_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        visited: Set[str] = set()
        queue = [(source_id, [source_id])]
        while queue:
            current, path = queue.pop(0)
            if current == target_id:
                return path
            if current in visited:
                continue
            visited.add(current)
            for child in self._adjacency.get(current, []):
                queue.append((child, path + [child]))
        return None

    def get_nodes_by_type(self, node_type: LineageType) -> List[LineageNode]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_dependencies(self, node_id: str) -> Dict[str, List[str]]:
        return {
            "upstream": self._reverse.get(node_id, []),
            "downstream": self._adjacency.get(node_id, []),
        }

    def get_provenance(self, node_id: str) -> Dict[str, Any]:
        if node_id not in self._nodes:
            return {}
        node = self._nodes[node_id]
        upstream = self.get_upstream(node_id)
        return {
            "node": node.to_dict(),
            "direct_sources": self._reverse.get(node_id, []),
            "all_sources": upstream,
            "source_count": len(upstream),
        }

    def to_graph(self) -> Dict[str, Any]:
        return {
            "nodes": {k: v.to_dict() for k, v in self._nodes.items()},
            "edges": [e.to_dict() for e in self._edges],
            "stats": {
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
            },
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_graph(), f, indent=2, default=str)

    def import_graph(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for nid, nd in data.get("nodes", {}).items():
            self.register_node(LineageNode(
                id=nd["id"], name=nd["name"], node_type=LineageType(nd["node_type"]),
                description=nd["description"], created_at=nd.get("created_at", time.time()),
                status=LineageStatus(nd.get("status", "active")),
                metadata=nd.get("metadata", {}), tags=nd.get("tags", []),
            ))
        for ed in data.get("edges", []):
            self.add_edge(ed["source_id"], ed["target_id"], ed["edge_type"], ed.get("metadata", {}))

    def stats(self) -> Dict[str, Any]:
        type_counts: Dict[str, int] = {}
        for n in self._nodes.values():
            type_counts[n.node_type.value] = type_counts.get(n.node_type.value, 0) + 1
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "by_type": type_counts,
            "avg_out_degree": sum(len(v) for v in self._adjacency.values()) / max(len(self._adjacency), 1),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Data Lineage Engine")
    print("=" * 60)

    engine = DataLineageEngine()

    # Register nodes
    nodes = [
        LineageNode("raw_1", "Raw Customer Data", LineageType.DATASET, "Original CSV from CRM", time.time()),
        LineageNode("clean_1", "Cleaned Data", LineageType.TRANSFORMATION, "Deduplicated and normalized", time.time()),
        LineageNode("feat_1", "Feature Store", LineageType.TRANSFORMATION, "Engineered features", time.time()),
        LineageNode("model_1", "Churn Prediction Model", LineageType.MODEL, "XGBoost classifier", time.time()),
        LineageNode("pipeline_1", "Training Pipeline", LineageType.PIPELINE, "End-to-end training", time.time()),
        LineageNode("api_1", "Prediction API", LineageType.EXTERNAL, "REST endpoint", time.time()),
    ]
    for n in nodes:
        engine.register_node(n)

    # Build edges
    edges = [
        ("raw_1", "clean_1"), ("clean_1", "feat_1"), ("feat_1", "pipeline_1"),
        ("pipeline_1", "model_1"), ("model_1", "api_1"), ("feat_1", "model_1"),
    ]
    for src, tgt in edges:
        engine.add_edge(src, tgt, "produces")
        print(f"  Edge: {src} -> {tgt}")

    print("\n--- Stats ---")
    print(engine.stats())

    print("\n--- Upstream of model_1 ---")
    upstream = engine.get_upstream("model_1")
    print(f"  {upstream}")

    print("\n--- Downstream of clean_1 ---")
    downstream = engine.get_downstream("clean_1")
    print(f"  {downstream}")

    print("\n--- Impact Analysis: feat_1 ---")
    impact = engine.impact_analysis("feat_1")
    print(f"  Upstream: {impact.upstream}")
    print(f"  Downstream: {impact.downstream}")
    print(f"  Total affected: {impact.total_affected}")

    print("\n--- Path: raw_1 -> api_1 ---")
    path = engine.get_lineage_path("raw_1", "api_1")
    print(f"  {' -> '.join(path) if path else 'No path'}")

    print("\n--- Provenance: model_1 ---")
    prov = engine.get_provenance("model_1")
    print(f"  Direct sources: {prov['direct_sources']}")
    print(f"  All sources: {prov['all_sources']}")
    print(f"  Source count: {prov['source_count']}")

    print("\n--- Graph Export ---")
    graph = engine.to_graph()
    print(f"  Nodes: {graph['stats']['node_count']}, Edges: {graph['stats']['edge_count']}")

    print("\nData Lineage test complete.")


if __name__ == "__main__":
    run()
