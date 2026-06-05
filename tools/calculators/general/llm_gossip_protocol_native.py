"""Gossip Protocol / Epidemic Broadcast — native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum, auto
import random
import time
import hashlib

class GossipState(Enum):
    SUSCEPTIBLE = auto()
    INFECTED = auto()
    REMOVED = auto()

@dataclass
class GossipNode:
    node_id: str
    state: GossipState = GossipState.SUSCEPTIBLE
    data: Dict = field(default_factory=dict)
    version: int = 0

    def infect(self, data: Dict):
        self.state = GossipState.INFECTED
        self.data = data
        self.version += 1

    def remove(self):
        self.state = GossipState.REMOVED

    def digest(self) -> str:
        payload = str(sorted(self.data.items())) + str(self.version)
        return hashlib.sha256(payload.encode()).hexdigest()[:8]

    def stats(self) -> Dict:
        return {"id": self.node_id, "state": self.state.name, "version": self.version, "digest": self.digest()}

class GossipProtocol:
    def __init__(self, fanout: int = 2, gossip_rounds: int = 10):
        self.nodes: Dict[str, GossipNode] = {}
        self.fanout = fanout
        self.gossip_rounds = gossip_rounds
        self.rounds_done = 0

    def add_node(self, node_id: str):
        self.nodes[node_id] = GossipNode(node_id)

    def seed(self, node_id: str, data: Dict):
        if node_id in self.nodes:
            self.nodes[node_id].infect(data)

    def gossip_round(self) -> Dict:
        infected = [n for n in self.nodes.values() if n.state == GossipState.INFECTED]
        transmissions = 0
        for source in infected:
            targets = random.sample([n for n in self.nodes.values() if n.node_id != source.node_id], min(self.fanout, len(self.nodes) - 1))
            for target in targets:
                if target.state == GossipState.SUSCEPTIBLE:
                    target.infect(source.data)
                    transmissions += 1
                elif target.state == GossipState.INFECTED and target.version < source.version:
                    target.data = source.data
                    target.version = source.version
                    transmissions += 1
        self.rounds_done += 1
        return {"transmissions": transmissions, "infected": len([n for n in self.nodes.values() if n.state == GossipState.INFECTED])}

    def run_gossip(self, seed_node: str, seed_data: Dict) -> List[Dict]:
        self.seed(seed_node, seed_data)
        results = []
        for _ in range(self.gossip_rounds):
            results.append(self.gossip_round())
        return results

    def convergence(self) -> bool:
        return all(n.state == GossipState.INFECTED or n.state == GossipState.REMOVED for n in self.nodes.values())

    def stats(self) -> Dict:
        states = {}
        for n in self.nodes.values():
            states[n.state.name] = states.get(n.state.name, 0) + 1
        return {"nodes": len(self.nodes), "rounds": self.rounds_done, "states": states, "converged": self.convergence()}

def run():
    gp = GossipProtocol(fanout=2, gossip_rounds=5)
    for i in range(10):
        gp.add_node(f"N{i}")
    results = gp.run_gossip("N0", {"config": "v1.0", "timestamp": 12345})
    print("Rounds:", results)
    print(gp.stats())

if __name__ == "__main__":
    run()
