"""Node Manager - Distributed node management for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set
from enum import Enum, auto
import time

class NodeStatus(Enum):
    HEALTHY = auto(); UNHEALTHY = auto(); OFFLINE = auto()

@dataclass
class NodeManager:
    nodes: Dict[str, Dict] = field(default_factory=dict)

    def register(self, node_id: str, address: str, capacity: int = 10) -> None:
        self.nodes[node_id] = {"address": address, "capacity": capacity, "load": 0, "status": NodeStatus.HEALTHY, "last_heartbeat": time.time()}

    def heartbeat(self, node_id: str) -> None:
        if node_id in self.nodes:
            self.nodes[node_id]["last_heartbeat"] = time.time()
            self.nodes[node_id]["status"] = NodeStatus.HEALTHY

    def check_health(self, timeout: float = 30.0) -> List[str]:
        now = time.time(); unhealthy = []
        for nid, info in self.nodes.items():
            if now - info["last_heartbeat"] > timeout:
                info["status"] = NodeStatus.UNHEALTHY
                unhealthy.append(nid)
        return unhealthy

    def get_healthy_nodes(self) -> List[str]:
        return [nid for nid, info in self.nodes.items() if info["status"] == NodeStatus.HEALTHY]

    def stats(self) -> dict:
        return {"total": len(self.nodes), "healthy": len(self.get_healthy_nodes())}

def run():
    nm = NodeManager()
    nm.register("node1", "192.168.1.1", 10)
    nm.register("node2", "192.168.1.2", 8)
    nm.heartbeat("node1")
    print("Healthy:", nm.get_healthy_nodes())
    print("Stats:", nm.stats())

if __name__ == "__main__": run()
