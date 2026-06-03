"""Consensus Engine - Raft-style consensus for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class Role(Enum):
    FOLLOWER = auto(); CANDIDATE = auto(); LEADER = auto()

@dataclass
class ConsensusEngine:
    node_id: str = "node1"
    role: Role = Role.FOLLOWER
    term: int = 0
    votes: int = 0
    log: List[Dict] = field(default_factory=list)

    def request_vote(self, candidate_term: int, candidate_id: str) -> bool:
        if candidate_term > self.term:
            self.term = candidate_term
            self.role = Role.FOLLOWER
            return True
        return False

    def append_entries(self, leader_term: int, entries: List[Dict]) -> bool:
        if leader_term >= self.term:
            self.term = leader_term
            self.role = Role.FOLLOWER
            self.log.extend(entries)
            return True
        return False

    def stats(self) -> dict:
        return {"node": self.node_id, "role": self.role.name, "term": self.term, "log_len": len(self.log)}

def run():
    ce = ConsensusEngine("node1")
    print("Vote:", ce.request_vote(1, "node2"))
    print("Append:", ce.append_entries(1, [{"cmd": "set x=1"}]))
    print("Stats:", ce.stats())

if __name__ == "__main__": run()
