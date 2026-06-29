"""
visual_flow_builder_native.py
MAGNATRIX-OS — Visual Flow Builder

Inspired by langflow-ai/langflow visual node-based editor:
Build AI workflows with nodes, edges, and visual canvas. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class FlowNode:
    node_id: str
    node_type: str
    label: str
    position: Dict[str, int]  # x, y
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)


@dataclass
class FlowEdge:
    edge_id: str
    source: str
    target: str
    source_handle: str = ""
    target_handle: str = ""


@dataclass
class FlowCanvas:
    flow_id: str
    name: str
    nodes: List[FlowNode] = field(default_factory=list)
    edges: List[FlowEdge] = field(default_factory=list)


class VisualFlowBuilder:
    """Visual node-based flow builder for AI workflows."""

    NODE_TYPES = ["input", "prompt", "llm", "output", "memory", "tool", "agent", "condition", "vector_store"]

    def __init__(self, flows_dir: str = "./flows"):
        self.flows_dir = Path(flows_dir)
        self.flows_dir.mkdir(exist_ok=True)
        self.flows: Dict[str, FlowCanvas] = {}
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
                        self.flows[fid] = FlowCanvas(**fd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.flows_dir / "flows.json", "w", encoding="utf-8") as f:
            out = {}
            for fid, flow in self.flows.items():
                d = asdict(flow)
                d["nodes"] = [asdict(n) for n in flow.nodes]
                d["edges"] = [asdict(e) for e in flow.edges]
                out[fid] = d
            json.dump(out, f, indent=2)

    def create_flow(self, flow_id: str, name: str) -> FlowCanvas:
        flow = FlowCanvas(flow_id=flow_id, name=name)
        self.flows[flow_id] = flow
        self._save()
        return flow

    def add_node(self, flow_id: str, node_id: str, node_type: str, label: str,
                 x: int, y: int, config: Optional[Dict[str, Any]] = None) -> FlowNode:
        flow = self.flows.get(flow_id)
        if not flow:
            raise ValueError(f"Flow {flow_id} not found")
        node = FlowNode(
            node_id=node_id, node_type=node_type, label=label,
            position={"x": x, "y": y}, config=config or {},
        )
        flow.nodes.append(node)
        self._save()
        return node

    def connect(self, flow_id: str, edge_id: str, source: str, target: str) -> FlowEdge:
        flow = self.flows.get(flow_id)
        if not flow:
            raise ValueError(f"Flow {flow_id} not found")
        edge = FlowEdge(edge_id=edge_id, source=source, target=target)
        flow.edges.append(edge)
        self._save()
        return edge

    def remove_node(self, flow_id: str, node_id: str) -> bool:
        flow = self.flows.get(flow_id)
        if not flow:
            return False
        flow.nodes = [n for n in flow.nodes if n.node_id != node_id]
        flow.edges = [e for e in flow.edges if e.source != node_id and e.target != node_id]
        self._save()
        return True

    def get_flow(self, flow_id: str) -> Optional[FlowCanvas]:
        return self.flows.get(flow_id)

    def validate_flow(self, flow_id: str) -> List[str]:
        """Validate flow connectivity and configuration."""
        flow = self.flows.get(flow_id)
        if not flow:
            return ["Flow not found"]
        errors = []
        node_ids = {n.node_id for n in flow.nodes}
        for edge in flow.edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                errors.append(f"Edge {edge.edge_id} connects to non-existent node")
        # Check for disconnected nodes
        connected = set()
        for edge in flow.edges:
            connected.add(edge.source)
            connected.add(edge.target)
        for node in flow.nodes:
            if node.node_id not in connected and len(flow.nodes) > 1:
                errors.append(f"Node {node.node_id} is disconnected")
        return errors

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = sum(len(f.nodes) for f in self.flows.values())
        total_edges = sum(len(f.edges) for f in self.flows.values())
        return {"flows": len(self.flows), "total_nodes": total_nodes, "total_edges": total_edges}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["VisualFlowBuilder", "FlowNode", "FlowEdge", "FlowCanvas"]