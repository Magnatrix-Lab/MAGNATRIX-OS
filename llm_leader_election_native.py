"""Leader Election — Bully & Ring algorithms, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum, auto
import random
import time

class NodeState(Enum):
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()

@dataclass
class Node:
    node_id: int
    state: NodeState = NodeState.FOLLOWER
    leader_id: Optional[int] = None
    alive: bool = True

class BullyElection:
    def __init__(self, nodes: List[Node]):
        self.nodes = {n.node_id: n for n in nodes}

    def elect(self, initiator_id: int) -> Optional[int]:
        initiator = self.nodes.get(initiator_id)
        if not initiator or not initiator.alive:
            return None
        higher = [nid for nid, n in self.nodes.items() if nid > initiator_id and n.alive]
        if not higher:
            initiator.state = NodeState.LEADER
            for n in self.nodes.values():
                n.leader_id = initiator_id
            return initiator_id
        responses = []
        for nid in higher:
            responses.append(nid)
        if responses:
            return self.elect(max(responses))
        return None

    def kill_node(self, node_id: int):
        if node_id in self.nodes:
            self.nodes[node_id].alive = False
            self.nodes[node_id].state = NodeState.FOLLOWER

    def stats(self) -> Dict:
        return {nid: {"state": n.state.name, "alive": n.alive, "leader": n.leader_id} for nid, n in self.nodes.items()}

class RingElection:
    def __init__(self, nodes: List[int]):
        self.ring = sorted(nodes)
        self.leader: Optional[int] = None

    def elect(self, initiator: int) -> int:
        if initiator not in self.ring:
            raise ValueError("Initiator not in ring")
        idx = self.ring.index(initiator)
        alive = self.ring[:]
        current = idx
        candidates = [initiator]
        visited = 0
        while visited < len(alive):
            nid = alive[current % len(alive)]
            if nid > max(candidates):
                candidates.append(nid)
            current = (current + 1) % len(alive)
            visited += 1
        self.leader = max(candidates)
        return self.leader

    def stats(self) -> Dict:
        return {"ring": self.ring, "leader": self.leader}

def run():
    nodes = [Node(i) for i in range(1, 6)]
    bully = BullyElection(nodes)
    leader = bully.elect(2)
    print("Bully leader:", leader, bully.stats())
    bully.kill_node(5)
    leader = bully.elect(4)
    print("After kill 5:", leader, bully.stats())
    ring = RingElection([1, 2, 3, 4, 5])
    print("Ring leader:", ring.elect(3), ring.stats())

if __name__ == "__main__":
    run()
