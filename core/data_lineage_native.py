#!/usr/bin/env python3
"""
Data Lineage for MAGNATRIX-OS
Data flow tracking, input -> process -> output -> storage, audit trail.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional


class LineageNode:
    """Single node in data lineage graph."""

    def __init__(self, node_id: str, node_type: str, name: str, metadata: Dict[str, Any] = None) -> None:
        self.node_id = node_id
        self.node_type = node_type  # 'input', 'process', 'output', 'storage'
        self.name = name
        self.metadata = metadata or {}
        self.timestamp = time.time()
        self.data_hash = ''

    def set_data_hash(self, data: Any) -> None:
        self.data_hash = hashlib.sha256(str(data).encode()).hexdigest()[:16]


class LineageEdge:
    """Edge connecting two lineage nodes."""

    def __init__(self, from_node: str, to_node: str, operation: str) -> None:
        self.from_node = from_node
        self.to_node = to_node
        self.operation = operation
        self.timestamp = time.time()


class DataLineage:
    """Data lineage tracking system."""

    def __init__(self, storage_path: str = './lineage.json') -> None:
        self._storage_path = storage_path
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: List[LineageEdge] = []
        self._traces: Dict[str, str] = {}  # trace_id -> start_node_id

    def start_trace(self, trace_id: Optional[str] = None, source: str = 'unknown') -> str:
        tid = trace_id or str(uuid.uuid4())[:8]
        node = LineageNode(tid, 'input', source)
        self._nodes[tid] = node
        self._traces[tid] = tid
        return tid

    def add_process(self, trace_id: str, process_name: str, input_data: Any, metadata: Dict[str, Any] = None) -> str:
        node_id = f"{trace_id}_{len([n for n in self._nodes if n.startswith(trace_id)])}"
        node = LineageNode(node_id, 'process', process_name, metadata)
        node.set_data_hash(input_data)
        self._nodes[node_id] = node

        # Find previous node in this trace
        prev_nodes = [n for n in self._nodes if n.startswith(trace_id) and n != node_id]
        if prev_nodes:
            edge = LineageEdge(prev_nodes[-1], node_id, process_name)
            self._edges.append(edge)

        return node_id

    def add_output(self, trace_id: str, output_name: str, output_data: Any, metadata: Dict[str, Any] = None) -> str:
        node_id = f"{trace_id}_output_{int(time.time())}"
        node = LineageNode(node_id, 'output', output_name, metadata)
        node.set_data_hash(output_data)
        self._nodes[node_id] = node

        # Connect to last process
        process_nodes = [n for n in self._nodes if n.startswith(trace_id) and n.startswith(f'{trace_id}_')]
        if process_nodes:
            edge = LineageEdge(process_nodes[-1], node_id, 'output')
            self._edges.append(edge)

        return node_id

    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        nodes = [n for nid, n in self._nodes.items() if nid.startswith(trace_id)]
        return [{
            'id': n.node_id,
            'type': n.node_type,
            'name': n.name,
            'hash': n.data_hash,
            'timestamp': n.timestamp,
        } for n in sorted(nodes, key=lambda x: x.timestamp)]

    def audit_trail(self, trace_id: str) -> str:
        trace = self.get_trace(trace_id)
        return ' -> '.join(f"[{n['type']}] {n['name']}" for n in trace)

    def list_traces(self) -> List[str]:
        return list(self._traces.keys())

    def stats(self) -> Dict[str, int]:
        return {
            'traces': len(self._traces),
            'nodes': len(self._nodes),
            'edges': len(self._edges),
        }


def _demo() -> None:
    print("=== Data Lineage Demo ===\n")

    lineage = DataLineage()

    # Start trace
    trace = lineage.start_trace(source='user_query')

    # Add processing steps
    lineage.add_process(trace, 'query_parser', 'How do I use RAG?', {'parser': 'nlp'})
    lineage.add_process(trace, 'retriever', 'RAG documents', {'method': 'hybrid_search'})
    lineage.add_process(trace, 'llm_inference', 'Retrieved context', {'model': 'llama3.2:3b'})
    lineage.add_output(trace, 'answer', 'RAG is a technique...', {'tokens': 150})

    # Show trace
    print("Trace:")
    for node in lineage.get_trace(trace):
        print(f"  [{node['type']}] {node['name']} (hash: {node['hash']})")

    print(f"\nAudit trail: {lineage.audit_trail(trace)}")
    print(f"Stats: {lineage.stats()}")

    print("\n=== Data Lineage Demo Complete ===")


if __name__ == '__main__':
    _demo()
