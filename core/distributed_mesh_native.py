#!/usr/bin/env python3
"""
core/distributed_mesh_native.py
MAGNATRIX-OS — Distributed Mesh Inference Coordinator
AMATI pattern: multi-node inference, load balancing, failover, mesh networking

Pure Python, stdlib only. Simulates node registry, task partitioning,
load balancing, and result aggregation across distributed nodes.
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


# ───────────────────────────────────────────────────────────────
# 1. NODE REGISTRY
# ───────────────────────────────────────────────────────────────

@dataclass
class ComputeNode:
    node_id: str
    host: str
    port: int
    vram_gb: float
    speed_tps: float  # tokens per second
    supported_models: List[str] = field(default_factory=list)
    status: str = "online"
    last_heartbeat: float = 0.0
    load: float = 0.0  # 0-1


class NodeRegistry:
    """Register and track compute nodes."""

    def __init__(self) -> None:
        self._nodes: Dict[str, ComputeNode] = {}

    def register(self, node: ComputeNode) -> None:
        node.last_heartbeat = _now()
        self._nodes[node.node_id] = node

    def heartbeat(self, node_id: str) -> bool:
        if node_id in self._nodes:
            self._nodes[node_id].last_heartbeat = _now()
            return True
        return False

    def get_node(self, node_id: str) -> Optional[ComputeNode]:
        return self._nodes.get(node_id)

    def list_nodes(self, status: Optional[str] = None) -> List[ComputeNode]:
        nodes = list(self._nodes.values())
        if status:
            nodes = [n for n in nodes if n.status == status]
        return nodes

    def check_stale(self, timeout: float = 30.0) -> List[str]:
        stale = []
        for nid, node in self._nodes.items():
            if _now() - node.last_heartbeat > timeout:
                node.status = "stale"
                stale.append(nid)
        return stale

    def stats(self) -> Dict[str, Any]:
        return {"total": len(self._nodes), "online": len([n for n in self._nodes.values() if n.status == "online"])}


# ───────────────────────────────────────────────────────────────
# 2. TASK PARTITIONER
# ───────────────────────────────────────────────────────────────

class TaskPartitioner:
    """Split large inference tasks across multiple nodes."""

    def partition(self, prompt: str, nodes: List[ComputeNode]) -> List[Tuple[str, str]]:
        if not nodes:
            return []
        words = prompt.split()
        chunk_size = max(1, len(words) // len(nodes))
        partitions = []
        for i, node in enumerate(nodes):
            start = i * chunk_size
            end = start + chunk_size if i < len(nodes) - 1 else len(words)
            chunk = " ".join(words[start:end])
            partitions.append((node.node_id, chunk))
        return partitions


# ───────────────────────────────────────────────────────────────
# 3. LOAD BALANCER
# ───────────────────────────────────────────────────────────────

class LoadBalancer:
    """Distribute requests across nodes."""

    STRATEGIES = ["round_robin", "least_latency", "least_load", "weighted"]

    def __init__(self, strategy: str = "least_load") -> None:
        self.strategy = strategy
        self._counter = 0

    def select(self, nodes: List[ComputeNode]) -> Optional[ComputeNode]:
        if not nodes:
            return None
        if self.strategy == "round_robin":
            self._counter += 1
            return nodes[self._counter % len(nodes)]
        elif self.strategy == "least_latency":
            return min(nodes, key=lambda n: 1.0 / n.speed_tps)
        elif self.strategy == "least_load":
            return min(nodes, key=lambda n: n.load)
        elif self.strategy == "weighted":
            total = sum(n.vram_gb for n in nodes)
            r = random.uniform(0, total)
            cumulative = 0.0
            for n in nodes:
                cumulative += n.vram_gb
                if r <= cumulative:
                    return n
            return nodes[-1]
        return nodes[0]


# ───────────────────────────────────────────────────────────────
# 4. MESH COORDINATOR
# ───────────────────────────────────────────────────────────────

class MeshCoordinator:
    """Coordinate multi-node inference and synchronize results."""

    def __init__(self, registry: NodeRegistry, balancer: LoadBalancer) -> None:
        self.registry = registry
        self.balancer = balancer
        self._results: Dict[str, Any] = {}

    def distribute(self, task_id: str, prompt: str) -> Dict[str, Any]:
        nodes = self.registry.list_nodes("online")
        if not nodes:
            return {"success": False, "error": "No online nodes available"}

        partitioner = TaskPartitioner()
        partitions = partitioner.partition(prompt, nodes)

        distributed = []
        for node_id, chunk in partitions:
            node = self.registry.get_node(node_id)
            if node:
                node.load = min(1.0, node.load + 0.1)
                distributed.append({"node_id": node_id, "chunk": chunk, "model": node.supported_models[0] if node.supported_models else "unknown"})

        return {"success": True, "task_id": task_id, "partitions": len(distributed), "nodes": [d["node_id"] for d in distributed]}

    def collect(self, task_id: str, partial_results: List[str]) -> str:
        return " ".join(partial_results)


# ───────────────────────────────────────────────────────────────
# 5. FAILOVER MANAGER
# ───────────────────────────────────────────────────────────────

class FailoverManager:
    """Detect node failures and redistribute tasks."""

    def __init__(self, registry: NodeRegistry, coordinator: MeshCoordinator) -> None:
        self.registry = registry
        self.coordinator = coordinator

    def check_failures(self) -> List[str]:
        stale = self.registry.check_stale(timeout=30.0)
        for nid in stale:
            node = self.registry.get_node(nid)
            if node:
                node.status = "failed"
        return stale

    def redistribute(self, task_id: str, failed_node_id: str, prompt: str) -> Dict[str, Any]:
        nodes = self.registry.list_nodes("online")
        if not nodes:
            return {"success": False, "error": "No nodes available for failover"}
        return self.coordinator.distribute(f"{task_id}_failover", prompt)


# ───────────────────────────────────────────────────────────────
# 6. RESULT AGGREGATOR
# ───────────────────────────────────────────────────────────────

class ResultAggregator:
    """Combine partial results from multiple nodes."""

    def aggregate(self, partial_results: List[str], strategy: str = "concatenate") -> str:
        if strategy == "concatenate":
            return " ".join(partial_results)
        elif strategy == "best":
            return max(partial_results, key=len) if partial_results else ""
        elif strategy == "vote":
            # Simple voting by frequency
            counts: Dict[str, int] = {}
            for r in partial_results:
                counts[r] = counts.get(r, 0) + 1
            return max(counts, key=counts.get) if counts else ""
        return " ".join(partial_results)

    def rank(self, partial_results: List[str], scores: List[float]) -> List[Tuple[str, float]]:
        ranked = list(zip(partial_results, scores))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked


# ───────────────────────────────────────────────────────────────
# 7. MESH OPTIMIZER
# ───────────────────────────────────────────────────────────────

class MeshOptimizer:
    """Auto-optimize node placement based on task characteristics."""

    def optimize(self, task_type: str, model_id: str, nodes: List[ComputeNode]) -> List[ComputeNode]:
        # Filter nodes that support the model
        candidates = [n for n in nodes if model_id in n.supported_models]
        if not candidates:
            candidates = nodes

        # Sort by capability for task type
        if task_type == "reasoning":
            candidates.sort(key=lambda n: n.vram_gb, reverse=True)
        elif task_type == "streaming":
            candidates.sort(key=lambda n: n.speed_tps, reverse=True)
        elif task_type == "batch":
            candidates.sort(key=lambda n: n.load)

        return candidates[:3]  # Top 3 nodes


# ───────────────────────────────────────────────────────────────
# 8. DISTRIBUTED MESH
# ───────────────────────────────────────────────────────────────

class DistributedMesh:
    """Main orchestrator: register -> partition -> balance -> coordinate -> aggregate -> optimize."""

    def __init__(self) -> None:
        self.registry = NodeRegistry()
        self.balancer = LoadBalancer("least_load")
        self.coordinator = MeshCoordinator(self.registry, self.balancer)
        self.failover = FailoverManager(self.registry, self.coordinator)
        self.aggregator = ResultAggregator()
        self.optimizer = MeshOptimizer()

    def register_node(self, node_id: str, host: str, port: int, vram_gb: float, speed_tps: float, models: List[str]) -> None:
        node = ComputeNode(node_id, host, port, vram_gb, speed_tps, models)
        self.registry.register(node)

    def infer(self, task_id: str, prompt: str, model_id: str = "magnatrix-7b", task_type: str = "general") -> Dict[str, Any]:
        nodes = self.registry.list_nodes("online")
        optimized = self.optimizer.optimize(task_type, model_id, nodes)

        if not optimized:
            return {"success": False, "error": "No suitable nodes found"}

        distribution = self.coordinator.distribute(task_id, prompt)
        if not distribution["success"]:
            return distribution

        # Simulate partial results
        partials = [f"[Node {n.node_id}] Processed chunk" for n in optimized[:distribution["partitions"]]]
        final = self.aggregator.aggregate(partials, "concatenate")

        return {
            "success": True,
            "task_id": task_id,
            "model_id": model_id,
            "nodes_used": distribution["nodes"],
            "partitions": distribution["partitions"],
            "result": final,
        }

    def health_check(self) -> Dict[str, Any]:
        stale = self.registry.check_stale()
        return {
            "nodes": self.registry.stats(),
            "stale_nodes": stale,
            "strategy": self.balancer.strategy,
        }

    def stats(self) -> Dict[str, Any]:
        return {"nodes": self.registry.stats(), "strategy": self.balancer.strategy}


# ───────────────────────────────────────────────────────────────
# 9. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Distributed Mesh Demo")
    print("=" * 60)

    mesh = DistributedMesh()

    # Register nodes
    print("\n[1] Registering nodes...")
    mesh.register_node("node_1", "192.168.1.10", 8080, 80.0, 50.0, ["magnatrix-7b", "llama-3-8b"])
    mesh.register_node("node_2", "192.168.1.11", 8080, 24.0, 120.0, ["magnatrix-7b", "gpt-4o-mini"])
    mesh.register_node("node_3", "192.168.1.12", 8080, 48.0, 80.0, ["llama-3-70b", "deepseek-v2"])
    mesh.register_node("node_4", "192.168.1.13", 8080, 16.0, 200.0, ["magnatrix-7b", "phi-3"])
    print(f"  Registered: {mesh.registry.stats()['total']} nodes")

    # Distributed inference
    print("\n[2] Distributed inference...")
    task = "Explain quantum computing in detail with examples and applications"
    result = mesh.infer("task_001", task, model_id="magnatrix-7b", task_type="reasoning")
    print(f"  Task: {task[:50]}...")
    print(f"  Success: {result['success']}")
    print(f"  Nodes used: {result['nodes_used']}")
    print(f"  Partitions: {result['partitions']}")
    print(f"  Result: {result['result'][:80]}...")

    # Health check
    print("\n[3] Health check...")
    health = mesh.health_check()
    print(f"  Nodes: {health['nodes']}")
    print(f"  Strategy: {health['strategy']}")

    # Failover simulation
    print("\n[4] Failover test...")
    stale = mesh.registry.check_stale(timeout=0.1)  # Force stale with tiny timeout
    print(f"  Stale nodes: {stale}")

    # Load balancer strategies
    print("\n[5] Load balancer strategies...")
    for strategy in LoadBalancer.STRATEGIES:
        mesh.balancer.strategy = strategy
        selected = mesh.balancer.select(mesh.registry.list_nodes("online"))
        print(f"  {strategy}: selected {selected.node_id if selected else 'none'} (load={selected.load if selected else 0:.2f})")

    print(f"\n[STATS] {json.dumps(mesh.stats(), indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. Distributed Mesh ready for MAGNATRIX-OS.")
    print("=" * 60)
