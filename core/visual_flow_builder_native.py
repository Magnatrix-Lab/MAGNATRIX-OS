"""
visual_flow_builder_native.py
MAGNATRIX-OS — Visual Flow Builder

Inspired by Langflow (langflow-ai): Visual drag-and-drop AI workflow builder.
Define flows with nodes and edges, serialize to JSON, and validate. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class FlowNode:
    node_id: str
    node_type: str
    label: str
    position: Dict[str, float] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)


@dataclass
class FlowEdge:
    edge_id: str
    source: str
    target: str
    label: str = ""
    condition: str = ""


@dataclass
class Flow:
    flow_id: str
    name: str
    description: str
    nodes: List[FlowNode] = field(default_factory=list)
    edges: List[FlowEdge] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class VisualFlowBuilder:
    """Visual drag-and-drop AI workflow builder."""

    NODE_TYPES = [
        "chat_input", "chat_output", "prompt", "llm", "memory",
        "agent", "tool", "condition", "loop", "aggregator",
        "text_splitter", "embedding", "vector_store", "retriever",
    ]

    def __init__(self, flows_dir: str = "./flows"):
        self.flows_dir = Path(flows_dir)
        self.flows_dir.mkdir(exist_ok=True)
        self.flows: Dict[str, Flow] = {}
        self._load()

    def _load(self) -> None:
        file = self.flows_dir / "flows.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for fid, fd in data.items():
                        fd["nodes"] = [FlowNode(**n) for n in fd.get("nodes", [])]
                        fd["edges"] = [FlowEdge(**e) for e in fd.get("edges", [])]
                        self.flows[fid] = Flow(**fd)
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for fid, f in self.flows.items():
            d = asdict(f)
            d["nodes"] = [asdict(n) for n in f.nodes]
            d["edges"] = [asdict(e) for e in f.edges]
            out[fid] = d
        with open(self.flows_dir / "flows.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def create_flow(self, flow_id: str, name: str, description: str = "") -> Flow:
        flow = Flow(flow_id=flow_id, name=name, description=description)
        self.flows[flow_id] = flow
        self._save()
        return flow

    def add_node(self, flow_id: str, node_id: str, node_type: str, label: str,
                 x: float = 0.0, y: float = 0.0, data: Optional[Dict[str, Any]] = None) -> bool:
        flow = self.flows.get(flow_id)
        if not flow or node_type not in self.NODE_TYPES:
            return False
        node = FlowNode(
            node_id=node_id, node_type=node_type, label=label,
            position={"x": x, "y": y}, data=data or {},
        )
        flow.nodes.append(node)
        flow.updated_at = datetime.now().isoformat()
        self._save()
        return True

    def add_edge(self, flow_id: str, edge_id: str, source: str, target: str, label: str = "") -> bool:
        flow = self.flows.get(flow_id)
        if not flow:
            return False
        edge = FlowEdge(edge_id=edge_id, source=source, target=target, label=label)
        flow.edges.append(edge)
        flow.updated_at = datetime.now().isoformat()
        self._save()
        return True

    def remove_node(self, flow_id: str, node_id: str) -> bool:
        flow = self.flows.get(flow_id)
        if not flow:
            return False
        flow.nodes = [n for n in flow.nodes if n.node_id != node_id]
        flow.edges = [e for e in flow.edges if e.source != node_id and e.target != node_id]
        self._save()
        return True

    def validate(self, flow_id: str) -> List[str]:
        flow = self.flows.get(flow_id)
        if not flow:
            return ["Flow not found"]
        errors = []
        node_ids = {n.node_id for n in flow.nodes}
        for e in flow.edges:
            if e.source not in node_ids:
                errors.append(f"Edge {e.edge_id}: source node {e.source} not found")
            if e.target not in node_ids:
                errors.append(f"Edge {e.edge_id}: target node {e.target} not found")
        disconnected = [n.node_id for n in flow.nodes if not any(e.source == n.node_id or e.target == n.node_id for e in flow.edges)]
        if len(flow.nodes) > 1 and disconnected:
            errors.append(f"Disconnected nodes: {disconnected}")
        return errors

    def export(self, flow_id: str) -> Optional[str]:
        flow = self.flows.get(flow_id)
        if not flow:
            return None
        d = asdict(flow)
        d["nodes"] = [asdict(n) for n in flow.nodes]
        d["edges"] = [asdict(e) for e in flow.edges]
        return json.dumps(d, indent=2)

    def get_flow(self, flow_id: str) -> Optional[Flow]:
        return self.flows.get(flow_id)

    def list_flows(self) -> List[Flow]:
        return list(self.flows.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.flows)
        total_nodes = sum(len(f.nodes) for f in self.flows.values())
        total_edges = sum(len(f.edges) for f in self.flows.values())
        return {"flows": total, "nodes": total_nodes, "edges": total_edges}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["VisualFlowBuilder", "Flow", "FlowNode", "FlowEdge"]