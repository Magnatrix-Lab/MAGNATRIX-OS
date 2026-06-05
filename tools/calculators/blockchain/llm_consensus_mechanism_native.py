"""Consensus Mechanism — PoW, PoS, PoA voting, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import hashlib
import random
import time

class ConsensusType(Enum):
    POW = auto()
    POS = auto()
    POA = auto()
    DPOS = auto()

@dataclass
class BlockProposal:
    block_id: str
    proposer: str
    timestamp: float
    difficulty: int = 0

class ConsensusMechanism:
    def __init__(self, consensus_type: ConsensusType = ConsensusType.POW):
        self.consensus_type = consensus_type
        self.stakes: Dict[str, float] = {}
        self.authorities: List[str] = []
        self.difficulty = 4
        self.proposals: List[BlockProposal] = []
        self.votes: Dict[str, List[str]] = {}

    def add_stake(self, node: str, amount: float):
        self.stakes[node] = self.stakes.get(node, 0) + amount

    def add_authority(self, node: str):
        if node not in self.authorities:
            self.authorities.append(node)

    def mine_pow(self, block_id: str, proposer: str) -> Tuple[str, int]:
        nonce = 0
        target = "0" * self.difficulty
        while True:
            data = f"{block_id}:{proposer}:{nonce}"
            h = hashlib.sha256(data.encode()).hexdigest()
            if h.startswith(target):
                return h, nonce
            nonce += 1
            if nonce > 100000:
                break
        return "", -1

    def select_pos_validator(self) -> str:
        total = sum(self.stakes.values())
        if total == 0:
            return ""
        pick = random.uniform(0, total)
        current = 0
        for node, stake in self.stakes.items():
            current += stake
            if current >= pick:
                return node
        return ""

    def select_poa_validator(self) -> str:
        if not self.authorities:
            return ""
        return random.choice(self.authorities)

    def validate(self, proposal: BlockProposal) -> bool:
        if self.consensus_type == ConsensusType.POW:
            h, nonce = self.mine_pow(proposal.block_id, proposal.proposer)
            return h != ""
        elif self.consensus_type == ConsensusType.POS:
            return proposal.proposer == self.select_pos_validator()
        elif self.consensus_type == ConsensusType.POA:
            return proposal.proposer in self.authorities
        return False

    def vote(self, block_id: str, voter: str):
        if block_id not in self.votes:
            self.votes[block_id] = []
        self.votes[block_id].append(voter)

    def tally_votes(self, block_id: str) -> int:
        return len(self.votes.get(block_id, []))

    def stats(self) -> Dict:
        return {"type": self.consensus_type.name, "stakes": len(self.stakes), "authorities": len(self.authorities), "difficulty": self.difficulty}

def run():
    consensus = ConsensusMechanism(ConsensusType.POW)
    consensus.difficulty = 2
    h, nonce = consensus.mine_pow("block1", "miner1")
    print("Hash:", h[:16], "Nonce:", nonce)
    consensus2 = ConsensusMechanism(ConsensusType.POS)
    consensus2.add_stake("v1", 100)
    consensus2.add_stake("v2", 50)
    print("POS validator:", consensus2.select_pos_validator())
    print(consensus.stats())

if __name__ == "__main__":
    run()
