"""Data Lineage — tracking data flow, transformations, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum, auto
import time
import uuid

class LineageType(Enum):
    SOURCE = auto()
    TRANSFORM = auto()
    JOIN = auto()
    AGGREGATE = auto()
    SINK = auto()

@dataclass
class LineageNode:
    node_id: str
    node_type: LineageType
    name: str
    schema: Dict[str, str] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

class DataLineageTracker:
    def __init__(self):
        self.nodes: Dict[str, LineageNode] = {}
        self.edges: List[Tuple[str, str]] = []
        self.datasets: Dict[str, Dict] = {}

    def register_dataset(self, dataset_id: str, schema: Dict[str, str], source: str = ""):
        self.datasets[dataset_id] = {"schema": schema, "source": source, "transformations": []}
        node_id = str(uuid.uuid4())[:8]
        self.nodes[node_id] = LineageNode(node_id, LineageType.SOURCE, dataset_id, schema)
        return node_id

    def add_transformation(self, input_ids: List[str], output_id: str, transform_name: str, transform_type: LineageType = LineageType.TRANSFORM) -> str:
        node_id = str(uuid.uuid4())[:8]
        input_schemas = [self.nodes[i].schema for i in input_ids if i in self.nodes]
        merged_schema = {}
        for s in input_schemas:
            merged_schema.update(s)
        self.nodes[node_id] = LineageNode(node_id, transform_type, transform_name, merged_schema, input_ids, [output_id])
        for i in input_ids:
            self.edges.append((i, node_id))
        self.edges.append((node_id, output_id))
        if output_id in self.datasets:
            self.datasets[output_id]["transformations"].append(transform_name)
        return node_id

    def get_upstream(self, node_id: str, depth: int = 10) -> List[str]:
        upstream = []
        to_visit = [(node_id, 0)]
        visited = {node_id}
        while to_visit:
            current, d = to_visit.pop(0)
            if d >= depth:
                continue
            for edge in self.edges:
                if edge[1] == current and edge[0] not in visited:
                    visited.add(edge[0])
                    upstream.append(edge[0])
                    to_visit.append((edge[0], d + 1))
        return upstream

    def get_downstream(self, node_id: str, depth: int = 10) -> List[str]:
        downstream = []
        to_visit = [(node_id, 0)]
        visited = {node_id}
        while to_visit:
            current, d = to_visit.pop(0)
            if d >= depth:
                continue
            for edge in self.edges:
                if edge[0] == current and edge[1] not in visited:
                    visited.add(edge[1])
                    downstream.append(edge[1])
                    to_visit.append((edge[1], d + 1))
        return downstream

    def stats(self) -> Dict:
        return {"nodes": len(self.nodes), "edges": len(self.edges), "datasets": len(self.datasets), "types": {t.name for t in set(n.node_type for n in self.nodes.values())}}

def run():
    tracker = DataLineageTracker()
    raw = tracker.register_dataset("raw_sales", {"id": "int", "amount": "float"})
    clean = tracker.register_dataset("clean_sales", {"id": "int", "amount": "float"})
    agg = tracker.register_dataset("monthly_agg", {"month": "str", "total": "float"})
    t1 = tracker.add_transformation([raw], clean, "clean_data")
    t2 = tracker.add_transformation([clean], agg, "aggregate", LineageType.AGGREGATE)
    print("Upstream of agg:", tracker.get_upstream(agg))
    print(tracker.stats())

if __name__ == "__main__":
    run()
