#!/usr/bin/env python3
"""Smart City Grid for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

@dataclass
class GridNode:
    node_id: str
    energy_load: float = 0.0
    traffic_flow: float = 0.0
    sensor_data: Dict[str, float] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

class SmartCityGrid:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.nodes: Dict[str, GridNode] = {}
        self.total_energy = 0.0
    def add_node(self, node: GridNode):
        self.nodes[node.node_id] = node
    def distribute_energy(self, amount: float) -> Dict[str, float]:
        if not self.nodes: return {}
        per_node = amount / len(self.nodes)
        allocation = {}
        for nid, node in self.nodes.items():
            node.energy_load = min(node.capacity if hasattr(node, 'capacity') else 100, per_node)
            allocation[nid] = node.energy_load
        return allocation
    def to_dict(self): return {"nodes": len(self.nodes), "total_energy": self.total_energy}
