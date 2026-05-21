#!/usr/bin/env python3
"""
Swarm Orchestrator — MAGNATRIX Phase 4-5
Scales brain instances from 5 → 1000+. Auto-spawns, load-balances, heals.
"""

import json
import random
from typing import Dict, List
from datetime import datetime

class SwarmOrchestrator:
    """Manages thousands of brain instances as one collective intelligence."""

    BRAIN_TYPES = ["trading", "coding", "research", "security", "coordination", "memory", "inference"]

    def __init__(self):
        self.nodes = {}
        self.node_counter = 0
        self.health_threshold = 0.3

    def spawn(self, brain_type: str, count: int = 1) -> List[str]:
        """Auto-spawn new brain instances."""
        spawned = []
        for _ in range(count):
            self.node_counter += 1
            node_id = f"brain-{brain_type}-{self.node_counter:04d}"
            self.nodes[node_id] = {
                "type": brain_type,
                "status": "active",
                "health": 1.0,
                "load": 0.0,
                "spawned_at": datetime.now().isoformat(),
                "capabilities": self._get_capabilities(brain_type),
            }
            spawned.append(node_id)
        return spawned

    def _get_capabilities(self, brain_type: str) -> List[str]:
        caps = {
            "trading": ["signal_gen", "risk_mgmt", "execution", "arbitrage"],
            "coding": ["code_gen", "debug", "refactor", "review"],
            "research": ["web_search", "synthesis", "hypothesis", "experiment_design"],
            "security": ["scan", "pentest", "monitor", "respond"],
            "coordination": ["delegate", "schedule", "resolve", "report"],
            "memory": ["store", "retrieve", "index", "forget"],
            "inference": ["predict", "classify", "embed", "generate"],
        }
        return caps.get(brain_type, ["general"])

    def load_balance(self, task: Dict) -> str:
        """Route task to healthiest, least-loaded node."""
        candidates = [n for n, info in self.nodes.items() if info["status"] == "active" and info["health"] > self.health_threshold]
        if not candidates:
            # Spawn new node if all overloaded
            new_nodes = self.spawn(task.get("type", "general"), 2)
            candidates = new_nodes

        # Select by lowest load + highest health
        best = min(candidates, key=lambda n: self.nodes[n]["load"] / max(self.nodes[n]["health"], 0.01))
        self.nodes[best]["load"] += 0.1
        return best

    def heal(self):
        """Detect and heal degraded nodes."""
        healed = 0
        for node_id, info in list(self.nodes.items()):
            if info["health"] < self.health_threshold:
                if info["health"] < 0.1:
                    # Kill and respawn
                    info["status"] = "restarting"
                    new_nodes = self.spawn(info["type"], 1)
                    info["status"] = "replaced"
                    print(f"🔄 Node {node_id} replaced by {new_nodes[0]}")
                else:
                    # Reduce load
                    info["load"] = max(0, info["load"] - 0.3)
                    info["health"] = min(1.0, info["health"] + 0.2)
                    healed += 1
        return healed

    def get_swarm_status(self) -> Dict:
        """Full swarm status."""
        by_type = {}
        for info in self.nodes.values():
            t = info["type"]
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "active": sum(1 for n in self.nodes.values() if n["status"] == "active"),
            "by_type": by_type,
            "avg_health": sum(n["health"] for n in self.nodes.values()) / max(len(self.nodes), 1),
            "avg_load": sum(n["load"] for n in self.nodes.values()) / max(len(self.nodes), 1),
        }

    def save(self):
        with open("collective-brain/swarm_state.json", "w") as f:
            json.dump({
                "nodes": self.nodes,
                "total_count": self.node_counter,
            }, f, indent=2)

if __name__ == "__main__":
    swarm = SwarmOrchestrator()
    print("=== Swarm Orchestrator ===")

    # Initial swarm: 5 nodes
    for bt in ["trading", "coding", "research", "security", "coordination"]:
        swarm.spawn(bt, 1)
    print(f"Initial: {len(swarm.nodes)} nodes
")

    # Scale to 20
    print("📈 Scaling to 20 nodes...")
    for bt in swarm.BRAIN_TYPES:
        swarm.spawn(bt, random.randint(1, 3))
    print(f"Swarm: {len(swarm.nodes)} nodes")

    # Simulate load
    for _ in range(10):
        task = {"type": random.choice(swarm.BRAIN_TYPES)}
        node = swarm.load_balance(task)

    # Heal
    healed = swarm.heal()
    print(f"Healed: {healed} nodes")

    status = swarm.get_swarm_status()
    print(f"
📊 Status: {status['active']}/{status['total_nodes']} active")
    print(f"   By type: {status['by_type']}")
    print(f"   Avg health: {status['avg_health']:.2f} | Avg load: {status['avg_load']:.2f}")

    swarm.save()
