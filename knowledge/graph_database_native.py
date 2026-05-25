#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Graph Database (Layer 5 Extension)
Property graph with nodes + edges, Cypher-like query language,
graph traversal (BFS/DFS), shortest path, and PageRank.
================================================================================
Zero-dependency graph database with adjacency list storage.
================================================================================
"""
from __future__ import annotations
from storage.file_ops_native import open as _secure_open

import hashlib
import heapq
import json
import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union


# =============================================================================
# Constants
# =============================================================================
DEFAULT_GRAPH_DIR = "/tmp/magnatrix_graphdb"


# =============================================================================
# Data Types
# =============================================================================
@dataclass
class Node:
    node_id: str
    labels: Set[str] = field(default_factory=set)
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def __hash__(self) -> int:
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return False
        return self.node_id == other.node_id


@dataclass
class Edge:
    edge_id: str
    source_id: str
    target_id: str
    rel_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def __hash__(self) -> int:
        return hash(self.edge_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Edge):
            return False
        return self.edge_id == other.edge_id


@dataclass
class Path:
    nodes: List[Node]
    edges: List[Edge]
    cost: float = 0.0

    @property
    def length(self) -> int:
        return len(self.edges)


# =============================================================================
# Query Parser
# =============================================================================
class GraphQuery:
    """Simple Cypher-like query parser."""

    # MATCH (n:Label {prop: value})-[r:TYPE]->(m:Label) WHERE ... RETURN ...
    MATCH_RE = re.compile(
        r"MATCH\s+\((\w+)(?::(\w+))?\s*(?:\{([^}]*)\})?\)\s*"
        r"(?:-\[(\w+)?(?::(\w+))?\s*(?:\{([^}]*)\})?\]->\s*\((\w+)(?::(\w+))?\s*(?:\{([^}]*)\})?\)\s*)?"
        r"(?:WHERE\s+(.+?)\s+)?"
        r"RETURN\s+(.+)",
        re.IGNORECASE,
    )

    def __init__(self, query_str: str) -> None:
        self.raw = query_str
        self.nodes: Dict[str, Tuple[Optional[str], Optional[Dict[str, Any]]]] = {}
        self.rel: Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]] = (None, None, None)
        self.where: Optional[str] = None
        self.returns: List[str] = []
        self._parse()

    def _parse_props(self, prop_str: str) -> Dict[str, Any]:
        props: Dict[str, Any] = {}
        if not prop_str:
            return props
        for kv in prop_str.split(","):
            if ":" in kv:
                k, v = kv.split(":", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                try:
                    v = int(v)
                except ValueError:
                    try:
                        v = float(v)
                    except ValueError:
                        v = v.lower() == "true" if v.lower() in ("true", "false") else v
                props[k] = v
        return props

    def _parse(self) -> None:
        m = self.MATCH_RE.match(self.raw)
        if not m:
            return
        groups = m.groups()
        # Node 1
        self.nodes[groups[0]] = (groups[1], self._parse_props(groups[2] or ""))
        # Relationship
        if groups[3] or groups[4]:
            self.rel = (groups[3], groups[4], self._parse_props(groups[5] or ""))
        # Node 2
        if groups[6]:
            self.nodes[groups[6]] = (groups[7], self._parse_props(groups[8] or ""))
        # WHERE
        self.where = groups[9]
        # RETURN
        if groups[10]:
            self.returns = [r.strip() for r in groups[10].split(",")]


# =============================================================================
# Graph Storage
# =============================================================================
class GraphStorage:
    """In-memory graph with file persistence."""

    def __init__(self, db_dir: str = DEFAULT_GRAPH_DIR) -> None:
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}
        self._adj_out: Dict[str, Set[str]] = {}  # node_id -> edge_ids
        self._adj_in: Dict[str, Set[str]] = {}   # node_id -> edge_ids
        self._label_index: Dict[str, Set[str]] = {}  # label -> node_ids
        self._type_index: Dict[str, Set[str]] = {}  # rel_type -> edge_ids
        self._lock = threading.Lock()
        self._dirty = False
        self._load()

    def _load(self) -> None:
        nodes_path = self.db_dir / "nodes.json"
        edges_path = self.db_dir / "edges.json"
        if nodes_path.exists():
            with open(nodes_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for nid, ndata in data.items():
                self._nodes[nid] = Node(
                    node_id=nid,
                    labels=set(ndata.get("labels", [])),
                    properties=ndata.get("properties", {}),
                    created_at=ndata.get("created_at", time.time()),
                )
        if edges_path.exists():
            with open(edges_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for eid, edata in data.items():
                self._edges[eid] = Edge(
                    edge_id=eid,
                    source_id=edata["source"],
                    target_id=edata["target"],
                    rel_type=edata["type"],
                    properties=edata.get("properties", {}),
                    created_at=edata.get("created_at", time.time()),
                )
                self._add_to_indices(self._edges[eid])

    def _add_to_indices(self, edge: Edge) -> None:
        self._adj_out.setdefault(edge.source_id, set()).add(edge.edge_id)
        self._adj_in.setdefault(edge.target_id, set()).add(edge.edge_id)
        self._type_index.setdefault(edge.rel_type, set()).add(edge.edge_id)

    def _remove_from_indices(self, edge: Edge) -> None:
        self._adj_out.get(edge.source_id, set()).discard(edge.edge_id)
        self._adj_in.get(edge.target_id, set()).discard(edge.edge_id)
        self._type_index.get(edge.rel_type, set()).discard(edge.edge_id)

    def add_node(self, node_id: str, labels: Optional[Set[str]] = None, properties: Optional[Dict[str, Any]] = None) -> Node:
        node = Node(node_id=node_id, labels=labels or set(), properties=properties or {})
        with self._lock:
            self._nodes[node_id] = node
            for label in node.labels:
                self._label_index.setdefault(label, set()).add(node_id)
            self._dirty = True
        return node

    def add_edge(self, source_id: str, target_id: str, rel_type: str, edge_id: Optional[str] = None, properties: Optional[Dict[str, Any]] = None) -> Edge:
        eid = edge_id or f"{source_id}-{rel_type}-{target_id}-{int(time.time()*1000)}"
        edge = Edge(
            edge_id=eid,
            source_id=source_id,
            target_id=target_id,
            rel_type=rel_type,
            properties=properties or {},
        )
        with self._lock:
            self._edges[eid] = edge
            self._add_to_indices(edge)
            self._dirty = True
        return edge

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        return self._edges.get(edge_id)

    def delete_node(self, node_id: str) -> bool:
        with self._lock:
            node = self._nodes.pop(node_id, None)
            if not node:
                return False
            for label in node.labels:
                self._label_index.get(label, set()).discard(node_id)
            # Remove connected edges
            for eid in list(self._adj_out.get(node_id, [])):
                self._remove_edge(eid)
            for eid in list(self._adj_in.get(node_id, [])):
                self._remove_edge(eid)
            self._dirty = True
            return True

    def _remove_edge(self, edge_id: str) -> None:
        edge = self._edges.pop(edge_id, None)
        if edge:
            self._remove_from_indices(edge)

    def delete_edge(self, edge_id: str) -> bool:
        with self._lock:
            self._remove_edge(edge_id)
            self._dirty = True
            return True

    def nodes_by_label(self, label: str) -> List[Node]:
        ids = self._label_index.get(label, set())
        return [self._nodes[i] for i in ids if i in self._nodes]

    def edges_by_type(self, rel_type: str) -> List[Edge]:
        ids = self._type_index.get(rel_type, set())
        return [self._edges[i] for i in ids if i in self._edges]

    def neighbors(self, node_id: str, direction: str = "out") -> List[Node]:
        edge_ids = self._adj_out.get(node_id, set()) if direction == "out" else self._adj_in.get(node_id, set())
        if direction == "both":
            edge_ids = self._adj_out.get(node_id, set()) | self._adj_in.get(node_id, set())
        result = []
        for eid in edge_ids:
            edge = self._edges.get(eid)
            if edge:
                nid = edge.target_id if direction == "out" else edge.source_id
                if nid != node_id:
                    node = self._nodes.get(nid)
                    if node:
                        result.append(node)
        return result

    def degree(self, node_id: str) -> Tuple[int, int, int]:
        """Return (in_degree, out_degree, total_degree)."""
        in_d = len(self._adj_in.get(node_id, set()))
        out_d = len(self._adj_out.get(node_id, set()))
        return in_d, out_d, in_d + out_d

    def flush(self) -> None:
        with self._lock:
            if not self._dirty:
                return
            nodes_data = {}
            for nid, node in self._nodes.items():
                nodes_data[nid] = {
                    "labels": list(node.labels),
                    "properties": node.properties,
                    "created_at": node.created_at,
                }
            edges_data = {}
            for eid, edge in self._edges.items():
                edges_data[eid] = {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "type": edge.rel_type,
                    "properties": edge.properties,
                    "created_at": edge.created_at,
                }
            with open(self.db_dir / "nodes.json", "w", encoding="utf-8") as f:
                json.dump(nodes_data, f, indent=2, default=str)
            with open(self.db_dir / "edges.json", "w", encoding="utf-8") as f:
                json.dump(edges_data, f, indent=2, default=str)
            self._dirty = False

    def stats(self) -> Dict[str, int]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "labels": len(self._label_index),
            "rel_types": len(self._type_index),
        }


# =============================================================================
# Graph Traversal
# =============================================================================
class GraphTraversal:
    """BFS, DFS, shortest path, and community detection."""

    def __init__(self, storage: GraphStorage) -> None:
        self.storage = storage

    def bfs(self, start_id: str, target_id: Optional[str] = None, max_depth: int = 10) -> List[Path]:
        """Breadth-first search."""
        start = self.storage.get_node(start_id)
        if not start:
            return []
        paths: List[Path] = []
        queue: List[Tuple[Node, List[Node], List[Edge]]] = [(start, [start], [])]
        visited: Set[str] = {start_id}
        while queue:
            current, node_path, edge_path = queue.pop(0)
            if target_id and current.node_id == target_id:
                paths.append(Path(nodes=node_path, edges=edge_path))
                if len(paths) >= 100:  # Limit results
                    break
                continue
            if len(node_path) >= max_depth:
                continue
            for eid in self.storage._adj_out.get(current.node_id, set()):
                edge = self.storage.get_edge(eid)
                if edge and edge.target_id not in visited:
                    visited.add(edge.target_id)
                    target = self.storage.get_node(edge.target_id)
                    if target:
                        queue.append((target, node_path + [target], edge_path + [edge]))
        return paths

    def dfs(self, start_id: str, target_id: Optional[str] = None, max_depth: int = 10) -> List[Path]:
        """Depth-first search."""
        start = self.storage.get_node(start_id)
        if not start:
            return []
        paths: List[Path] = []
        visited: Set[str] = set()

        def visit(node: Node, node_path: List[Node], edge_path: List[Edge], depth: int) -> None:
            if target_id and node.node_id == target_id:
                paths.append(Path(nodes=list(node_path), edges=list(edge_path)))
                return
            if depth >= max_depth:
                return
            for eid in self.storage._adj_out.get(node.node_id, set()):
                edge = self.storage.get_edge(eid)
                if edge and edge.target_id not in visited:
                    visited.add(edge.target_id)
                    target = self.storage.get_node(edge.target_id)
                    if target:
                        node_path.append(target)
                        edge_path.append(edge)
                        visit(target, node_path, edge_path, depth + 1)
                        node_path.pop()
                        edge_path.pop()
                    visited.discard(edge.target_id)

        visited.add(start_id)
        visit(start, [start], [], 0)
        return paths

    def shortest_path(self, start_id: str, target_id: str, weight_prop: Optional[str] = None) -> Optional[Path]:
        """Dijkstra's shortest path."""
        start = self.storage.get_node(start_id)
        target = self.storage.get_node(target_id)
        if not start or not target:
            return None
        # Priority queue: (cost, node_id, path_nodes, path_edges)
        pq: List[Tuple[float, str, List[str], List[str]]] = [(0.0, start_id, [start_id], [])]
        visited: Set[str] = set()
        while pq:
            cost, nid, node_ids, edge_ids = heapq.heappop(pq)
            if nid in visited:
                continue
            visited.add(nid)
            if nid == target_id:
                nodes = [self.storage.get_node(i) for i in node_ids]
                edges = [self.storage.get_edge(i) for i in edge_ids]
                return Path(nodes=[n for n in nodes if n], edges=[e for e in edges if e], cost=cost)
            for eid in self.storage._adj_out.get(nid, set()):
                edge = self.storage.get_edge(eid)
                if edge and edge.target_id not in visited:
                    w = edge.properties.get(weight_prop, 1.0) if weight_prop else 1.0
                    heapq.heappush(pq, (cost + w, edge.target_id, node_ids + [edge.target_id], edge_ids + [eid]))
        return None

    def pagerank(self, damping: float = 0.85, iterations: int = 20) -> Dict[str, float]:
        """PageRank algorithm."""
        nodes = list(self.storage._nodes.keys())
        if not nodes:
            return {}
        n = len(nodes)
        scores: Dict[str, float] = {nid: 1.0 / n for nid in nodes}
        for _ in range(iterations):
            new_scores: Dict[str, float] = {}
            for nid in nodes:
                score = (1 - damping) / n
                for eid in self.storage._adj_in.get(nid, set()):
                    edge = self.storage.get_edge(eid)
                    if edge:
                        src = edge.source_id
                        out_degree = len(self.storage._adj_out.get(src, set()))
                        if out_degree > 0:
                            score += damping * scores.get(src, 0) / out_degree
                new_scores[nid] = score
            scores = new_scores
        return scores

    def connected_components(self) -> List[Set[str]]:
        """Find connected components using Union-Find."""
        parent: Dict[str, str] = {nid: nid for nid in self.storage._nodes}
        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(x: str, y: str) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        for edge in self.storage._edges.values():
            union(edge.source_id, edge.target_id)
        comps: Dict[str, Set[str]] = {}
        for nid in self.storage._nodes:
            root = find(nid)
            comps.setdefault(root, set()).add(nid)
        return list(comps.values())


# =============================================================================
# Graph Query Executor
# =============================================================================
class GraphQueryExecutor:
    """Execute parsed Cypher-like queries."""

    def __init__(self, storage: GraphStorage) -> None:
        self.storage = storage

    def execute(self, query: GraphQuery) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not query.nodes:
            return results
        # Simple pattern matching: (a)-[r]->(b)
        if query.rel[0] or query.rel[1]:
            # Need to find matching edges
            rel_type = query.rel[1]
            edges = self.storage.edges_by_type(rel_type) if rel_type else list(self.storage._edges.values())
            for edge in edges:
                src = self.storage.get_node(edge.source_id)
                tgt = self.storage.get_node(edge.target_id)
                if not src or not tgt:
                    continue
                # Check node filters
                match = True
                for var, (label, props) in query.nodes.items():
                    node = src if var == list(query.nodes.keys())[0] else tgt
                    if label and label not in node.labels:
                        match = False
                        break
                    if props and not all(node.properties.get(k) == v for k, v in props.items()):
                        match = False
                        break
                if not match:
                    continue
                # Check where clause (simplified)
                if query.where:
                    # Stub: evaluate simple where conditions
                    pass
                # Build result
                row: Dict[str, Any] = {}
                for ret in query.returns:
                    ret = ret.strip()
                    if "." in ret:
                        var, prop = ret.split(".", 1)
                        if var == list(query.nodes.keys())[0]:
                            row[ret] = src.properties.get(prop)
                        elif len(query.nodes) > 1 and var == list(query.nodes.keys())[1]:
                            row[ret] = tgt.properties.get(prop)
                        else:
                            row[ret] = edge.properties.get(prop)
                    else:
                        row[ret] = ret
                results.append(row)
        else:
            # Node-only query
            for var, (label, props) in query.nodes.items():
                candidates = self.storage.nodes_by_label(label) if label else list(self.storage._nodes.values())
                for node in candidates:
                    if props and not all(node.properties.get(k) == v for k, v in props.items()):
                        continue
                    row = {}
                    for ret in query.returns:
                        ret = ret.strip()
                        if "." in ret:
                            _, prop = ret.split(".", 1)
                            row[ret] = node.properties.get(prop)
                        else:
                            row[ret] = node.node_id
                    results.append(row)
        return results


# =============================================================================
# Graph Database Engine
# =============================================================================
class GraphDatabaseEngine:
    """Top-level graph database with query and traversal."""

    def __init__(self, db_dir: str = DEFAULT_GRAPH_DIR) -> None:
        self.storage = GraphStorage(db_dir)
        self.traversal = GraphTraversal(self.storage)
        self.query_executor = GraphQueryExecutor(self.storage)
        self._callbacks: List[Callable[[str, Any], None]] = []

    def on(self, event: str, callback: Callable[[str, Any], None]) -> None:
        self._callbacks.append(callback)

    def _emit(self, event: str, data: Any) -> None:
        for cb in self._callbacks:
            cb(event, data)

    def add_node(self, node_id: str, labels: Optional[Set[str]] = None, properties: Optional[Dict[str, Any]] = None) -> Node:
        node = self.storage.add_node(node_id, labels, properties)
        self._emit("node_added", node)
        return node

    def add_edge(self, source_id: str, target_id: str, rel_type: str, edge_id: Optional[str] = None, properties: Optional[Dict[str, Any]] = None) -> Edge:
        edge = self.storage.add_edge(source_id, target_id, rel_type, edge_id, properties)
        self._emit("edge_added", edge)
        return edge

    def query_cypher(self, query_str: str) -> List[Dict[str, Any]]:
        query = GraphQuery(query_str)
        return self.query_executor.execute(query)

    def shortest_path(self, start: str, end: str, weight: Optional[str] = None) -> Optional[Path]:
        return self.traversal.shortest_path(start, end, weight)

    def pagerank(self) -> Dict[str, float]:
        return self.traversal.pagerank()

    def neighbors(self, node_id: str, direction: str = "out") -> List[Node]:
        return self.storage.neighbors(node_id, direction)

    def delete_node(self, node_id: str) -> bool:
        return self.storage.delete_node(node_id)

    def delete_edge(self, edge_id: str) -> bool:
        return self.storage.delete_edge(edge_id)

    def stats(self) -> Dict[str, Any]:
        return self.storage.stats()

    def flush(self) -> None:
        self.storage.flush()

    def shutdown(self) -> None:
        self.flush()

    def __enter__(self) -> GraphDatabaseEngine:
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown()


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Graph Database Demo")
    print("=" * 60)
    gdb = GraphDatabaseEngine("/tmp/magnatrix_demo_graphdb")

    # Knowledge graph
    gdb.add_node("Alice", labels={"Person"}, properties={"age": 30, "role": "developer"})
    gdb.add_node("Bob", labels={"Person"}, properties={"age": 25, "role": "designer"})
    gdb.add_node("Charlie", labels={"Person"}, properties={"age": 35, "role": "manager"})
    gdb.add_node("ProjectX", labels={"Project"}, properties={"status": "active"})

    gdb.add_edge("Alice", "Bob", "KNOWS", properties={"since": 2020})
    gdb.add_edge("Bob", "Charlie", "KNOWS", properties={"since": 2021})
    gdb.add_edge("Charlie", "Alice", "KNOWS", properties={"since": 2019})
    gdb.add_edge("Alice", "ProjectX", "WORKS_ON")
    gdb.add_edge("Bob", "ProjectX", "WORKS_ON")

    print(f"Stats: {gdb.stats()}")

    # Query
    results = gdb.query_cypher("MATCH (n:Person {role: developer}) RETURN n.node_id, n.age")
    print(f"Developers: {results}")

    # Shortest path
    sp = gdb.shortest_path("Alice", "Charlie")
    if sp:
        print(f"Shortest Alice->Charlie: {[n.node_id for n in sp.nodes]} (cost={sp.cost:.1f})")

    # PageRank
    pr = gdb.pagerank()
    print(f"PageRank: {pr}")

    # Neighbors
    neighbors = gdb.neighbors("Alice")
    print(f"Alice's neighbors: {[n.node_id for n in neighbors]}")

    gdb.shutdown()
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
