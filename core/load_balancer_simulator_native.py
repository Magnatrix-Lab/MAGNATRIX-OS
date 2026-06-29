"""
load_balancer_simulator_native.py
MAGNATRIX-OS — Load Balancer Simulator

Inspired by donnemartin/system-design-primer load balancing:
Round-robin, least connections, weighted, consistent hashing, health checks. Pure stdlib.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class BackendNode:
    node_id: str
    address: str
    weight: int = 1
    active_connections: int = 0
    is_healthy: bool = True
    response_time_ms: float = 0.0
    total_requests: int = 0


class LoadBalancerSimulator:
    """Simulate load balancing algorithms and health checks."""

    def __init__(self, data_dir: str = "./load_balancer"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.nodes: List[BackendNode] = []
        self.rr_index = 0
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "nodes.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.nodes = [BackendNode(**n) for n in data]
            except Exception:
                pass
        idx_file = self.data_dir / "rr_index.json"
        if idx_file.exists():
            try:
                with open(idx_file, "r", encoding="utf-8") as f:
                    self.rr_index = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "nodes.json", "w", encoding="utf-8") as f:
            json.dump([asdict(n) for n in self.nodes], f, indent=2)
        with open(self.data_dir / "rr_index.json", "w", encoding="utf-8") as f:
            json.dump(self.rr_index, f)

    def add_node(self, node_id: str, address: str, weight: int = 1) -> BackendNode:
        node = BackendNode(node_id=node_id, address=address, weight=weight)
        self.nodes.append(node)
        self._save()
        return node

    def remove_node(self, node_id: str) -> bool:
        for i, n in enumerate(self.nodes):
            if n.node_id == node_id:
                del self.nodes[i]
                self._save()
                return True
        return False

    def round_robin(self) -> Optional[BackendNode]:
        healthy = [n for n in self.nodes if n.is_healthy]
        if not healthy:
            return None
        node = healthy[self.rr_index % len(healthy)]
        self.rr_index = (self.rr_index + 1) % len(healthy)
        node.total_requests += 1
        self._save()
        return node

    def least_connections(self) -> Optional[BackendNode]:
        healthy = [n for n in self.nodes if n.is_healthy]
        if not healthy:
            return None
        node = min(healthy, key=lambda n: n.active_connections)
        node.active_connections += 1
        node.total_requests += 1
        self._save()
        return node

    def weighted_round_robin(self) -> Optional[BackendNode]:
        healthy = [n for n in self.nodes if n.is_healthy]
        if not healthy:
            return None
        total_weight = sum(n.weight for n in healthy)
        if total_weight == 0:
            return None
        target = self.rr_index % total_weight
        current = 0
        for node in healthy:
            current += node.weight
            if current > target:
                self.rr_index = (self.rr_index + 1) % total_weight
                node.total_requests += 1
                self._save()
                return node
        return healthy[0]

    def consistent_hash(self, key: str) -> Optional[BackendNode]:
        healthy = [n for n in self.nodes if n.is_healthy]
        if not healthy:
            return None
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        node = healthy[h % len(healthy)]
        node.total_requests += 1
        self._save()
        return node

    def health_check(self, node_id: str, is_healthy: bool) -> bool:
        for n in self.nodes:
            if n.node_id == node_id:
                n.is_healthy = is_healthy
                self._save()
                return True
        return False

    def release_connection(self, node_id: str) -> bool:
        for n in self.nodes:
            if n.node_id == node_id and n.active_connections > 0:
                n.active_connections -= 1
                self._save()
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        healthy = sum(1 for n in self.nodes if n.is_healthy)
        total_req = sum(n.total_requests for n in self.nodes)
        return {"nodes": len(self.nodes), "healthy": healthy, "total_requests": total_req}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["LoadBalancerSimulator", "BackendNode"]