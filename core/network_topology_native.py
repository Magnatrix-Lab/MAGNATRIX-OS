#!/usr/bin/env python3
"""network_topology_native.py — MAGNATRIX-OS Network Topology Engine

Real-time module communication graph, domain clustering, bridge detection.
Inspired by brain network visualization (Power et al. 2011).
Pure stdlib.
"""
from __future__ import annotations
import json, threading, time, uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

@dataclass
class Node:
    id: str; domain: str; type: str = "module"; status: str = "active"
    connections: int = 0; throughput: float = 0.0; latency: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)

@dataclass
class Edge:
    source: str; target: str; weight: float = 1.0; type: str = "message"
    latency: float = 0.0; throughput: float = 0.0
    last_active: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Cluster:
    id: str; domain: str; nodes: List[str] = field(default_factory=list)
    density: float = 0.0; centrality: float = 0.0
    bridge_nodes: List[str] = field(default_factory=list)

class NetworkTopologyNative:
    DOMAIN_MAP: Dict[str, str] = {
        "vector_memory": "language", "knowledge_graph": "language", "identity": "language", "checkpoint": "language",
        "task_scheduler": "formal", "agent_messaging": "formal", "rbac": "formal", "security_scanner": "formal",
        "metrics_collector": "formal", "modularity_analyzer": "formal", "network_topology": "formal",
        "domain_isolation_test": "formal", "llm_gateway": "physical", "answer_fusion": "physical",
        "auto_recovery": "physical", "boot_optimizer": "physical",
        "deliberation_engine": "social", "human_in_loop": "social", "chat_interface": "social",
    }

    def __init__(self, workspace: str = "./network_topology") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self._nodes: Dict[str, Node] = {}; self._edges: Dict[str, Edge] = {}
        self._clusters: Dict[str, Cluster] = {}
        self._lock = threading.RLock()
        self._snapshots_path = self.workspace / "snapshots.jsonl"
        self._load()

    def _load(self) -> None:
        if self._snapshots_path.exists():
            try:
                with open(self._snapshots_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip(): continue
                        data = json.loads(line)
                        if data.get("type") == "node": self._nodes[data["id"]] = Node(**data["data"])
                        elif data.get("type") == "edge": key = f"{data['data']['source']}->{data['data']['target']}"; self._edges[key] = Edge(**data["data"])
            except Exception: pass

    def _save_snapshot(self, obj_type: str, data: Dict[str, Any]) -> None:
        with open(self._snapshots_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"type": obj_type, "timestamp": time.time(), "data": data}, default=str) + "
")

    def _extract_domain(self, module_id: str) -> str:
        for key, domain in self.DOMAIN_MAP.items():
            if key in module_id.lower(): return domain
        return "unknown"

    def register_node(self, module_id: str, node_type: str = "module", status: str = "active", metadata: Optional[Dict[str, Any]] = None) -> Node:
        with self._lock:
            domain = self._extract_domain(module_id)
            node = Node(id=module_id, domain=domain, type=node_type, status=status, metadata=metadata or {})
            self._nodes[module_id] = node; self._save_snapshot("node", asdict(node))
            return node

    def register_edge(self, source: str, target: str, weight: float = 1.0, edge_type: str = "message", latency: float = 0.0, throughput: float = 0.0) -> Edge:
        with self._lock:
            key = f"{source}->{target}"
            edge = Edge(source=source, target=target, weight=weight, type=edge_type, latency=latency, throughput=throughput)
            self._edges[key] = edge; self._save_snapshot("edge", asdict(edge))
            if source in self._nodes: self._nodes[source].connections += 1
            if target in self._nodes: self._nodes[target].connections += 1
            return edge

    def update_node(self, module_id: str, status: Optional[str] = None, throughput: Optional[float] = None, latency: Optional[float] = None) -> bool:
        with self._lock:
            if module_id not in self._nodes: return False
            node = self._nodes[module_id]
            if status: node.status = status
            if throughput is not None: node.throughput = throughput
            if latency is not None: node.latency = latency
            node.last_seen = time.time(); self._save_snapshot("node", asdict(node))
            return True

    def update_edge(self, source: str, target: str, weight: Optional[float] = None, latency: Optional[float] = None, throughput: Optional[float] = None) -> bool:
        with self._lock:
            key = f"{source}->{target}"
            if key not in self._edges: return False
            edge = self._edges[key]
            if weight is not None: edge.weight += weight
            if latency is not None: edge.latency = latency
            if throughput is not None: edge.throughput = throughput
            edge.last_active = time.time(); self._save_snapshot("edge", asdict(edge))
            return True

    def remove_node(self, module_id: str) -> bool:
        with self._lock:
            if module_id not in self._nodes: return False
            del self._nodes[module_id]
            to_remove = [k for k in self._edges if k.startswith(module_id + "->") or k.endswith("->" + module_id)]
            for k in to_remove: del self._edges[k]
            return True

    def remove_edge(self, source: str, target: str) -> bool:
        with self._lock:
            key = f"{source}->{target}"
            if key not in self._edges: return False
            del self._edges[key]
            return True

    def detect_clusters(self) -> Dict[str, Cluster]:
        with self._lock:
            clusters = {}; domain_nodes: Dict[str, List[str]] = {}
            for nid, node in self._nodes.items():
                if node.domain not in domain_nodes: domain_nodes[node.domain] = []
                domain_nodes[node.domain].append(nid)
            for domain, nodes in domain_nodes.items():
                intra_edges = [e for e in self._edges.values() if e.source in nodes and e.target in nodes]
                bridge = []
                for nid in nodes:
                    out_edges = [e for e in self._edges.values() if e.source == nid and e.target not in nodes]
                    in_edges = [e for e in self._edges.values() if e.target == nid and e.source not in nodes]
                    if out_edges or in_edges: bridge.append(nid)
                n = len(nodes)
                max_edges = n * (n - 1) if n > 1 else 1
                density = len(intra_edges) / max_edges
                degrees = sum(self._nodes[n].connections for n in nodes if n in self._nodes)
                centrality = degrees / n if n > 0 else 0
                cluster_id = f"cluster_{domain}_{int(time.time())}"
                clusters[domain] = Cluster(id=cluster_id, domain=domain, nodes=nodes, density=density, centrality=centrality, bridge_nodes=bridge)
            self._clusters = clusters
            return clusters

    def find_bridges(self) -> List[Tuple[str, str, str, str]]:
        with self._lock:
            bridges = []
            for edge in self._edges.values():
                src_domain = self._nodes.get(edge.source, Node("", "unknown")).domain
                tgt_domain = self._nodes.get(edge.target, Node("", "unknown")).domain
                if src_domain != tgt_domain and src_domain != "unknown" and tgt_domain != "unknown":
                    bridges.append((edge.source, src_domain, edge.target, tgt_domain))
            return bridges

    def detect_bottlenecks(self, threshold: float = 0.5) -> List[str]:
        with self._lock:
            bridges = self.find_bridges()
            bridge_count: Dict[str, int] = {}
            for src, _, tgt, _ in bridges:
                bridge_count[src] = bridge_count.get(src, 0) + 1
                bridge_count[tgt] = bridge_count.get(tgt, 0) + 1
            sorted_bridges = sorted(bridge_count.items(), key=lambda x: x[1], reverse=True)
            max_count = sorted_bridges[0][1] if sorted_bridges else 1
            return [n for n, c in sorted_bridges if c >= max_count * threshold]

    def get_shortest_path(self, start: str, end: str, max_hops: int = 10) -> Optional[List[str]]:
        with self._lock:
            if start not in self._nodes or end not in self._nodes: return None
            visited = {start: [start]}; queue = [start]
            while queue:
                current = queue.pop(0)
                if current == end: return visited[current]
                if len(visited[current]) >= max_hops: continue
                for edge in self._edges.values():
                    if edge.source == current and edge.target not in visited:
                        visited[edge.target] = visited[current] + [edge.target]
                        queue.append(edge.target)
            return None

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            clusters = self.detect_clusters(); bridges = self.find_bridges(); bottlenecks = self.detect_bottlenecks()
            domains = {}
            for node in self._nodes.values(): domains[node.domain] = domains.get(node.domain, 0) + 1
            return {"nodes": len(self._nodes), "edges": len(self._edges), "domains": len(domains), "domain_breakdown": domains, "clusters": {c.domain: {"nodes": len(c.nodes), "density": round(c.density, 4), "centrality": round(c.centrality, 4), "bridges": len(c.bridge_nodes)} for c in clusters.values()}, "cross_domain_bridges": len(bridges), "bottlenecks": bottlenecks, "average_connections": sum(n.connections for n in self._nodes.values()) / len(self._nodes) if self._nodes else 0}

    def export_graph(self, path: Optional[str] = None) -> str:
        with self._lock:
            graph = {"nodes": [asdict(n) for n in self._nodes.values()], "edges": [asdict(e) for e in self._edges.values()], "clusters": [asdict(c) for c in self._clusters.values()]}
            output_path = Path(path) if path else self.workspace / "graph.json"
            with open(output_path, "w", encoding="utf-8") as f: json.dump(graph, f, indent=2, default=str)
            return str(output_path)

    def print_summary(self) -> str:
        stats = self.get_stats()
        lines = ["=== Network Topology Summary ===", f"Nodes: {stats['nodes']} | Edges: {stats['edges']} | Domains: {stats['domains']}", f"Cross-Domain Bridges: {stats['cross_domain_bridges']}", f"Average Connections: {stats['average_connections']:.2f}", "
--- Domain Clusters ---"]
        for domain, c in stats['clusters'].items():
            lines.append(f"  {domain}: {c['nodes']} nodes, density={c['density']:.4f}, centrality={c['centrality']:.4f}, bridges={c['bridges']}")
        if stats['bottlenecks']:
            lines.append(f"
--- Bottlenecks ({len(stats['bottlenecks'])}) ---")
            for b in stats['bottlenecks']:
                node = self._nodes.get(b)
                if node: lines.append(f"  {b} ({node.domain}) — {node.connections} connections")
        return "
".join(lines)

if __name__ == "__main__":
    topo = NetworkTopologyNative()
    topo.register_node("vector_memory"); topo.register_node("knowledge_graph")
    topo.register_node("task_scheduler"); topo.register_node("agent_messaging")
    topo.register_node("deliberation_engine")
    topo.register_edge("vector_memory", "knowledge_graph", weight=2.0)
    topo.register_edge("knowledge_graph", "agent_messaging", weight=1.5)
    topo.register_edge("task_scheduler", "agent_messaging", weight=3.0)
    topo.register_edge("agent_messaging", "deliberation_engine", weight=1.0)
    print(topo.print_summary())
