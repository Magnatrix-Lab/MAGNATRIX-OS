# blockchain/consensus_native.py
# AMATI-PELAJARI-TIRU: Consensus Engine
# Layer blockchain of MAGNATRIX-OS — Distributed consensus
# PoS, BFT, Raft-like leader election, slashing, validator rotation

"""
Native Consensus Engine
=======================
Multi-strategy consensus for MAGNATRIX blockchain:
  - Proof of Stake (PoS): stake-weighted block production, delegation
  - BFT (Byzantine Fault Tolerance): 2/3 vote requirement, PBFT-style
  - Raft-like: leader election with heartbeat, log replication
  - Slashing: double-sign, downtime, equivocation penalties
  - Validator rotation: round-robin or VRF-based selection
  - Epoch management: validator set changes, reward distribution

Features:
  - Pure-Python consensus simulations
  - Deterministic validator selection with seed
  - Vote tallying with quorum enforcement
  - Validator score tracking (uptime, performance)
  - Reward/slash calculation per epoch
"""

from __future__ import annotations

import hashlib
import random
import time
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class ConsensusType(Enum):
    POS = auto()
    BFT = auto()
    RAFT = auto()


class ValidatorStatus(Enum):
    ACTIVE = auto()
    INACTIVE = auto()
    JAILED = auto()
    SLASHED = auto()


@dataclass
class Validator:
    address: str
    stake: float
    delegated: float = 0.0
    status: ValidatorStatus = ValidatorStatus.ACTIVE
    uptime: float = 1.0
    blocks_produced: int = 0
    blocks_missed: int = 0
    commission: float = 0.1  # 10% commission on rewards
    rewards: float = 0.0
    slashes: float = 0.0

    def total_stake(self) -> float:
        return self.stake + self.delegated

    def score(self) -> float:
        return self.total_stake() * self.uptime


@dataclass
class Vote:
    validator: str
    block_hash: str
    round_num: int
    signature: str
    timestamp: float


@dataclass
class Epoch:
    epoch_num: int
    start_block: int
    end_block: int
    validators: List[str] = field(default_factory=list)
    total_stake: float = 0.0
    reward_pool: float = 0.0


class ProofOfStake:
    """Proof of Stake consensus with stake-weighted selection."""

    def __init__(self, min_stake: float = 1000.0, block_time: float = 6.0):
        self.min_stake = min_stake
        self.block_time = block_time
        self.validators: Dict[str, Validator] = {}
        self.delegations: Dict[str, List[Tuple[str, float]]] = {}  # delegator -> [(validator, amount)]
        self.epochs: List[Epoch] = []
        self.current_epoch = 0
        self.blocks_per_epoch = 100

    def register_validator(self, address: str, stake: float, commission: float = 0.1) -> bool:
        if stake < self.min_stake:
            return False
        self.validators[address] = Validator(
            address=address, stake=stake, commission=commission,
        )
        return True

    def delegate(self, delegator: str, validator: str, amount: float) -> bool:
        val = self.validators.get(validator)
        if not val or val.status != ValidatorStatus.ACTIVE:
            return False
        val.delegated += amount
        self.delegations.setdefault(delegator, []).append((validator, amount))
        return True

    def select_proposer(self, block_height: int, seed: str = "") -> Optional[str]:
        active = [v for v in self.validators.values() if v.status == ValidatorStatus.ACTIVE]
        if not active:
            return None
        total = sum(v.total_stake() for v in active)
        if total == 0:
            return None
        # Deterministic VRF-like selection
        seed_hash = int(hashlib.sha256(f"{seed}:{block_height}".encode()).hexdigest(), 16)
        rand = (seed_hash % 1000000) / 1000000.0
        cumulative = 0.0
        for v in active:
            cumulative += v.total_stake() / total
            if rand <= cumulative:
                return v.address
        return active[-1].address

    def slash(self, validator: str, reason: str, percentage: float = 0.05) -> None:
        val = self.validators.get(validator)
        if not val:
            return
        slash_amount = val.total_stake() * percentage
        val.slashes += slash_amount
        val.stake -= slash_amount
        if val.stake < 0:
            val.stake = 0
        val.status = ValidatorStatus.JAILED

    def distribute_rewards(self, reward_pool: float) -> None:
        active = [v for v in self.validators.values() if v.status == ValidatorStatus.ACTIVE]
        total = sum(v.total_stake() for v in active)
        if total == 0:
            return
        for v in active:
            share = (v.total_stake() / total) * reward_pool
            commission = share * v.commission
            v.rewards += share - commission

    def get_validator_set(self) -> List[Validator]:
        return sorted(self.validators.values(), key=lambda v: v.total_stake(), reverse=True)

    def start_epoch(self, epoch_num: int, reward_pool: float) -> Epoch:
        active_addrs = [v.address for v in self.validators.values() if v.status == ValidatorStatus.ACTIVE]
        epoch = Epoch(
            epoch_num=epoch_num, start_block=epoch_num * self.blocks_per_epoch,
            end_block=(epoch_num + 1) * self.blocks_per_epoch - 1,
            validators=active_addrs, total_stake=sum(self.validators[a].total_stake() for a in active_addrs),
            reward_pool=reward_pool,
        )
        self.epochs.append(epoch)
        self.current_epoch = epoch_num
        return epoch


class BFTConsensus:
    """Practical Byzantine Fault Tolerance consensus."""

    def __init__(self, validators: List[str], f: int = 1):
        self.validators = set(validators)
        self.f = f  # max faulty nodes
        self.quorum = 2 * f + 1
        self.votes: Dict[int, Dict[str, List[Vote]]] = {}  # round -> block_hash -> votes
        self.round = 0

    def propose(self, block_hash: str, proposer: str) -> bool:
        if proposer not in self.validators:
            return False
        self.round += 1
        self.votes.setdefault(self.round, {}).setdefault(block_hash, [])
        return True

    def vote(self, validator: str, block_hash: str) -> bool:
        if validator not in self.validators:
            return False
        rnd = self.votes.setdefault(self.round, {})
        votes = rnd.setdefault(block_hash, [])
        vote = Vote(
            validator=validator, block_hash=block_hash, round_num=self.round,
            signature=hashlib.sha256(f"{validator}:{block_hash}:{self.round}".encode()).hexdigest()[:16],
            timestamp=time.time(),
        )
        votes.append(vote)
        return True

    def is_committed(self, block_hash: str) -> bool:
        votes = self.votes.get(self.round, {}).get(block_hash, [])
        return len(votes) >= self.quorum

    def get_commit_decision(self) -> Optional[str]:
        for block_hash, votes in self.votes.get(self.round, {}).items():
            if len(votes) >= self.quorum:
                return block_hash
        return None


class RaftConsensus:
    """Raft-like leader election and log replication."""

    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = peers
        self.term = 0
        self.state = "follower"  # follower, candidate, leader
        self.leader: Optional[str] = None
        self.votes_received: Set[str] = set()
        self.log: List[Dict[str, Any]] = []
        self.commit_index = 0
        self.last_heartbeat = time.time()
        self.election_timeout = random.uniform(0.15, 0.3)

    def start_election(self) -> None:
        self.state = "candidate"
        self.term += 1
        self.votes_received = {self.node_id}
        # Request votes from peers (simulated)
        for peer in self.peers:
            if self._request_vote(peer):
                self.votes_received.add(peer)
        if len(self.votes_received) > len(self.peers) // 2:
            self.state = "leader"
            self.leader = self.node_id

    def _request_vote(self, peer: str) -> bool:
        # Simulated: vote granted if term is higher
        return random.random() > 0.3

    def append_entries(self, entries: List[Dict[str, Any]]) -> bool:
        if self.state != "leader":
            return False
        for entry in entries:
            entry["term"] = self.term
            self.log.append(entry)
        return True

    def heartbeat(self) -> None:
        self.last_heartbeat = time.time()

    def check_timeout(self) -> bool:
        return time.time() - self.last_heartbeat > self.election_timeout

    def get_status(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "state": self.state,
            "term": self.term,
            "leader": self.leader,
            "log_length": len(self.log),
            "commit_index": self.commit_index,
        }


class ConsensusEngine:
    """Main consensus orchestrator with multi-strategy support."""

    def __init__(self, consensus_type: ConsensusType = ConsensusType.POS):
        self.consensus_type = consensus_type
        self.pos = ProofOfStake()
        self.bft: Optional[BFTConsensus] = None
        self.raft: Optional[RaftConsensus] = None

    def setup_pos(self, validators: List[Tuple[str, float]], min_stake: float = 1000.0) -> None:
        self.pos = ProofOfStake(min_stake=min_stake)
        for addr, stake in validators:
            self.pos.register_validator(addr, stake)
        self.consensus_type = ConsensusType.POS

    def setup_bft(self, validators: List[str], f: int = 1) -> None:
        self.bft = BFTConsensus(validators, f)
        self.consensus_type = ConsensusType.BFT

    def setup_raft(self, node_id: str, peers: List[str]) -> None:
        self.raft = RaftConsensus(node_id, peers)
        self.consensus_type = ConsensusType.RAFT

    def propose_block(self, block_hash: str, proposer: str) -> bool:
        if self.consensus_type == ConsensusType.BFT and self.bft:
            return self.bft.propose(block_hash, proposer)
        elif self.consensus_type == ConsensusType.RAFT and self.raft:
            return self.raft.append_entries([{"hash": block_hash}])
        return True

    def validate_block(self, block_hash: str, validator: str) -> bool:
        if self.consensus_type == ConsensusType.BFT and self.bft:
            return self.bft.vote(validator, block_hash)
        elif self.consensus_type == ConsensusType.POS:
            return validator in self.pos.validators
        return True

    def is_finalized(self, block_hash: str) -> bool:
        if self.consensus_type == ConsensusType.BFT and self.bft:
            return self.bft.is_committed(block_hash)
        elif self.consensus_type == ConsensusType.RAFT and self.raft:
            return self.raft.state == "leader"
        return True

    def get_status(self) -> Dict[str, Any]:
        if self.consensus_type == ConsensusType.POS:
            return {
                "type": "PoS", "validators": len(self.pos.validators),
                "total_stake": sum(v.total_stake() for v in self.pos.validators.values()),
                "epoch": self.pos.current_epoch,
            }
        elif self.consensus_type == ConsensusType.BFT and self.bft:
            return {"type": "BFT", "validators": len(self.bft.validators), "round": self.bft.round}
        elif self.consensus_type == ConsensusType.RAFT and self.raft:
            return self.raft.get_status()
        return {}


# --- Standalone test ---
if __name__ == "__main__":
    # PoS test
    engine = ConsensusEngine(ConsensusType.POS)
    engine.setup_pos([("val-1", 5000), ("val-2", 3000), ("val-3", 2000)])
    engine.pos.delegate("delegator-1", "val-1", 1000)
    proposer = engine.pos.select_proposer(1, seed="test")
    print(f"PoS proposer: {proposer}")
    epoch = engine.pos.start_epoch(1, 1000.0)
    print(f"Epoch {epoch.epoch_num}: validators={epoch.validators}, stake={epoch.total_stake}")

    # BFT test
    engine.setup_bft(["v1", "v2", "v3", "v4"], f=1)
    engine.propose_block("0xabc", "v1")
    engine.validate_block("0xabc", "v1")
    engine.validate_block("0xabc", "v2")
    engine.validate_block("0xabc", "v3")
    print(f"BFT committed: {engine.is_finalized('0xabc')}")

    # Raft test
    engine.setup_raft("node-1", ["node-2", "node-3"])
    engine.raft.start_election()
    print(f"Raft status: {engine.raft.get_status()}")
    print("Consensus engine ready.")
