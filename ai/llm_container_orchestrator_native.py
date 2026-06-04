"""Container Orchestrator - Pod scheduling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum, auto
import time

class ContainerStatus(Enum):
    PENDING = auto(); RUNNING = auto(); SUCCEEDED = auto(); FAILED = auto()

@dataclass
class ContainerOrchestrator:
    pods: Dict[str, Dict] = field(default_factory=dict)
    nodes: Dict[str, Dict] = field(default_factory=dict)

    def add_node(self, node_id: str, capacity: int = 10) -> None:
        self.nodes[node_id] = {"capacity": capacity, "pods": [], "available": capacity}

    def schedule_pod(self, pod_id: str, resources: int = 1) -> Optional[str]:
        candidates = sorted(self.nodes.items(), key=lambda x: x[1]["available"], reverse=True)
        for node_id, info in candidates:
            if info["available"] >= resources:
                info["pods"].append(pod_id)
                info["available"] -= resources
                self.pods[pod_id] = {"node": node_id, "resources": resources, "status": ContainerStatus.RUNNING}
                return node_id
        return None

    def delete_pod(self, pod_id: str) -> bool:
        if pod_id not in self.pods: return False
        node_id = self.pods[pod_id]["node"]
        resources = self.pods[pod_id]["resources"]
        self.nodes[node_id]["pods"].remove(pod_id)
        self.nodes[node_id]["available"] += resources
        del self.pods[pod_id]
        return True

    def stats(self) -> dict:
        return {"pods": len(self.pods), "nodes": len(self.nodes), "running": sum(1 for p in self.pods.values() if p["status"] == ContainerStatus.RUNNING)}

def run():
    co = ContainerOrchestrator()
    co.add_node("node1", 5); co.add_node("node2", 3)
    co.schedule_pod("pod1", 2); co.schedule_pod("pod2", 2); co.schedule_pod("pod3", 2)
    print("Pod assignments:", {k: v["node"] for k, v in co.pods.items()})
    print("Stats:", co.stats())

if __name__ == "__main__": run()
