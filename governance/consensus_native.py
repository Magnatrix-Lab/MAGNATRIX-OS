#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Consensus Engine (Layer 11 Extension)
Raft Consensus + BFT Voting for Distributed Governance
================================================================================
Zero-dependency consensus implementation: leader election, log replication,
commit safety, and Byzantine fault tolerance voting overlay.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Constants
# =============================================================================
ELECTION_TIMEOUT_MIN = 0.15
ELECTION_TIMEOUT_MAX = 0.30
HEARTBEAT_INTERVAL = 0.05
MAX_LOG_ENTRIES_PER_RPC = 100


# =============================================================================
# Roles
# =============================================================================
class NodeRole(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


# =============================================================================
# Log Entry
# =============================================================================
@dataclass
class LogEntry:
    term: int
    index: int
    command: Dict[str, Any]
    committed: bool = False
    checksum: str = ""

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        payload = f"{self.term}|{self.index}|{json.dumps(self.command, sort_keys=True)}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


# =============================================================================
# Raft Node
# =============================================================================
class RaftNode:
    """Single Raft consensus node with election and log replication."""

    def __init__(self, node_id: str, peers: List[str], transport: RaftTransport) -> None:
        self.node_id = node_id
        self.peers = [p for p in peers if p != node_id]
        self.transport = transport
        self.role = NodeRole.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0
        # Leader state
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}
        # Volatile
        self._election_deadline = time.time() + self._random_timeout()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[LogEntry], None]] = []
        self._state_machine: Dict[str, Any] = {}

    def _random_timeout(self) -> float:
        return ELECTION_TIMEOUT_MIN + random.random() * (ELECTION_TIMEOUT_MAX - ELECTION_TIMEOUT_MIN)

    def reset_election_timer(self) -> None:
        self._election_deadline = time.time() + self._random_timeout()

    def on_commit(self, callback: Callable[[LogEntry], None]) -> None:
        self._callbacks.append(callback)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._main_loop, daemon=True)
        self._thread.start()
        self.transport.register_node(self)

    def stop(self) -> None:
        self._running = False

    def _main_loop(self) -> None:
        while self._running:
            now = time.time()
            if self.role == NodeRole.FOLLOWER:
                if now >= self._election_deadline:
                    self._become_candidate()
            elif self.role == NodeRole.CANDIDATE:
                if now >= self._election_deadline:
                    self._become_candidate()
            elif self.role == NodeRole.LEADER:
                self._send_heartbeats()
                time.sleep(HEARTBEAT_INTERVAL)
                continue
            time.sleep(0.01)

    def _become_candidate(self) -> None:
        with self._lock:
            self.role = NodeRole.CANDIDATE
            self.current_term += 1
            self.voted_for = self.node_id
            self.reset_election_timer()
        self._request_votes()

    def _request_votes(self) -> None:
        last_log_index = len(self.log)
        last_log_term = self.log[-1].term if self.log else 0
        votes = 1
        granted = {self.node_id}
        for peer in self.peers:
            resp = self.transport.send_request_vote(
                peer,
                term=self.current_term,
                candidate_id=self.node_id,
                last_log_index=last_log_index,
                last_log_term=last_log_term,
            )
            if resp and resp.get("vote_granted"):
                votes += 1
                granted.add(peer)
        if votes > (len(self.peers) + 1) / 2:
            self._become_leader()

    def _become_leader(self) -> None:
        with self._lock:
            self.role = NodeRole.LEADER
            for peer in self.peers:
                self.next_index[peer] = len(self.log) + 1
                self.match_index[peer] = 0
        self._send_heartbeats()

    def _send_heartbeats(self) -> None:
        for peer in self.peers:
            prev_index = self.next_index.get(peer, 1) - 1
            prev_term = self.log[prev_index - 1].term if prev_index > 0 and prev_index <= len(self.log) else 0
            entries = self.log[prev_index:prev_index + MAX_LOG_ENTRIES_PER_RPC]
            self.transport.send_append_entries(
                peer,
                term=self.current_term,
                leader_id=self.node_id,
                prev_log_index=prev_index,
                prev_log_term=prev_term,
                entries=[{"term": e.term, "index": e.index, "command": e.command} for e in entries],
                leader_commit=self.commit_index,
            )

    def handle_request_vote(self, args: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            term = args.get("term", 0)
            if term > self.current_term:
                self.current_term = term
                self.role = NodeRole.FOLLOWER
                self.voted_for = None
            vote_granted = False
            if term == self.current_term and (self.voted_for is None or self.voted_for == args.get("candidate_id")):
                last_log_index = len(self.log)
                last_log_term = self.log[-1].term if self.log else 0
                candidate_last_index = args.get("last_log_index", 0)
                candidate_last_term = args.get("last_log_term", 0)
                if (candidate_last_term > last_log_term or
                    (candidate_last_term == last_log_term and candidate_last_index >= last_log_index)):
                    vote_granted = True
                    self.voted_for = args.get("candidate_id")
                    self.reset_election_timer()
            return {"term": self.current_term, "vote_granted": vote_granted}

    def handle_append_entries(self, args: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            term = args.get("term", 0)
            if term < self.current_term:
                return {"term": self.current_term, "success": False}
            if term > self.current_term:
                self.current_term = term
                self.voted_for = None
            self.role = NodeRole.FOLLOWER
            self.reset_election_timer()
            prev_log_index = args.get("prev_log_index", 0)
            if prev_log_index > 0:
                if prev_log_index > len(self.log) or self.log[prev_log_index - 1].term != args.get("prev_log_term", 0):
                    return {"term": self.current_term, "success": False}
            # Append new entries
            entries = args.get("entries", [])
            for i, raw in enumerate(entries):
                idx = prev_log_index + i + 1
                if idx <= len(self.log):
                    if self.log[idx - 1].term != raw["term"]:
                        self.log = self.log[:idx - 1]
                if idx > len(self.log):
                    self.log.append(LogEntry(term=raw["term"], index=raw["index"], command=raw["command"]))
            # Update commit index
            leader_commit = args.get("leader_commit", 0)
            if leader_commit > self.commit_index:
                self.commit_index = min(leader_commit, len(self.log))
            self._apply_committed()
            return {"term": self.current_term, "success": True}

    def _apply_committed(self) -> None:
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]
            entry.committed = True
            cmd = entry.command
            op = cmd.get("op")
            if op == "set":
                self._state_machine[cmd.get("key")] = cmd.get("value")
            elif op == "delete":
                self._state_machine.pop(cmd.get("key"), None)
            for cb in self._callbacks:
                cb(entry)

    def propose(self, command: Dict[str, Any]) -> bool:
        with self._lock:
            if self.role != NodeRole.LEADER:
                return False
            index = len(self.log) + 1
            entry = LogEntry(term=self.current_term, index=index, command=command)
            self.log.append(entry)
        return True

    def get_state(self, key: str) -> Any:
        return self._state_machine.get(key)

    @property
    def log_size(self) -> int:
        return len(self.log)


# =============================================================================
# Transport Interface
# =============================================================================
class RaftTransport(ABC):
    @abstractmethod
    def register_node(self, node: RaftNode) -> None: ...
    @abstractmethod
    def send_request_vote(self, peer: str, **kwargs: Any) -> Optional[Dict[str, Any]]: ...
    @abstractmethod
    def send_append_entries(self, peer: str, **kwargs: Any) -> Optional[Dict[str, Any]]: ...


class InMemoryTransport(RaftTransport):
    """In-memory transport for single-process testing."""

    def __init__(self) -> None:
        self._nodes: Dict[str, RaftNode] = {}
        self._latencies: Dict[Tuple[str, str], float] = {}

    def register_node(self, node: RaftNode) -> None:
        self._nodes[node.node_id] = node

    def set_latency(self, from_node: str, to_node: str, latency_sec: float) -> None:
        self._latencies[(from_node, to_node)] = latency_sec

    def send_request_vote(self, peer: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        target = self._nodes.get(peer)
        if not target:
            return None
        lat = self._latencies.get((kwargs.get("candidate_id", ""), peer), 0.0)
        if lat > 0:
            time.sleep(lat)
        return target.handle_request_vote(kwargs)

    def send_append_entries(self, peer: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        target = self._nodes.get(peer)
        if not target:
            return None
        lat = self._latencies.get((kwargs.get("leader_id", ""), peer), 0.0)
        if lat > 0:
            time.sleep(lat)
        return target.handle_append_entries(kwargs)


# =============================================================================
# BFT Voting Overlay
# =============================================================================
class BFTVoting:
    """Byzantine Fault Tolerant voting on top of Raft log consensus."""

    def __init__(self, raft: RaftNode, f: int = 1) -> None:
        """f = max faulty nodes tolerated."""
        self.raft = raft
        self.f = f
        self.proposals: Dict[str, Dict[str, Any]] = {}
        self.votes: Dict[str, Dict[str, bool]] = {}
        self._lock = threading.Lock()
        self._handlers: List[Callable[[str, bool], None]] = []

    def on_decision(self, handler: Callable[[str, bool], None]) -> None:
        self._handlers.append(handler)

    def propose_vote(self, proposal_id: str, command: Dict[str, Any]) -> bool:
        with self._lock:
            self.proposals[proposal_id] = command
            self.votes[proposal_id] = {}
        return self.raft.propose({"op": "vote", "proposal_id": proposal_id, "command": command})

    def cast_vote(self, proposal_id: str, voter: str, approve: bool) -> None:
        with self._lock:
            if proposal_id not in self.votes:
                self.votes[proposal_id] = {}
            self.votes[proposal_id][voter] = approve
            self._check_quorum(proposal_id)

    def _check_quorum(self, proposal_id: str) -> None:
        votes = self.votes.get(proposal_id, {})
        total = len(self.raft.peers) + 1
        approves = sum(1 for v in votes.values() if v)
        rejects = sum(1 for v in votes.values() if not v)
        threshold = (total + self.f) // 2 + 1
        if approves >= threshold:
            for h in self._handlers:
                h(proposal_id, True)
        elif rejects >= threshold:
            for h in self._handlers:
                h(proposal_id, False)

    def tally(self, proposal_id: str) -> Dict[str, Any]:
        with self._lock:
            return {
                "proposal": self.proposals.get(proposal_id),
                "votes": dict(self.votes.get(proposal_id, {})),
                "total_peers": len(self.raft.peers) + 1,
            }


# =============================================================================
# Cluster Manager
# =============================================================================
class RaftCluster:
    """Manages multiple Raft nodes in one process for testing/simulation."""

    def __init__(self, node_ids: List[str]) -> None:
        self.transport = InMemoryTransport()
        self.nodes: Dict[str, RaftNode] = {}
        for nid in node_ids:
            node = RaftNode(nid, node_ids, self.transport)
            self.nodes[nid] = node

    def start_all(self) -> None:
        for n in self.nodes.values():
            n.start()

    def stop_all(self) -> None:
        for n in self.nodes.values():
            n.stop()

    def wait_for_leader(self, timeout: float = 3.0) -> Optional[str]:
        t0 = time.time()
        while time.time() - t0 < timeout:
            for nid, n in self.nodes.items():
                if n.role == NodeRole.LEADER:
                    return nid
            time.sleep(0.05)
        return None

    def propose_through_leader(self, command: Dict[str, Any]) -> bool:
        leader = self.wait_for_leader()
        if leader:
            return self.nodes[leader].propose(command)
        return False

    def get_consensus_state(self, key: str) -> Any:
        # All nodes should have same committed state
        vals = [n.get_state(key) for n in self.nodes.values()]
        # Return majority value
        from collections import Counter
        c = Counter(v for v in vals if v is not None)
        if c:
            return c.most_common(1)[0][0]
        return None


# =============================================================================
# Governance Integration
# =============================================================================
class GovernanceConsensusBridge:
    """Connects governance proposals to Raft + BFT consensus."""

    def __init__(self, cluster: RaftCluster) -> None:
        self.cluster = cluster
        self._bft_nodes: Dict[str, BFTVoting] = {}

    def register_bft(self, node_id: str) -> BFTVoting:
        raft = self.cluster.nodes[node_id]
        bft = BFTVoting(raft)
        self._bft_nodes[node_id] = bft
        return bft

    def propose_policy(self, policy: Dict[str, Any]) -> str:
        pid = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()[:16]
        self.cluster.propose_through_leader({"op": "set", "key": f"policy:{pid}", "value": policy})
        return pid

    def get_policy(self, pid: str) -> Any:
        return self.cluster.get_consensus_state(f"policy:{pid}")


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Consensus Engine Demo")
    print("=" * 60)
    cluster = RaftCluster(["n1", "n2", "n3", "n4", "n5"])
    cluster.start_all()
    leader = cluster.wait_for_leader(timeout=2.0)
    print(f"Elected leader: {leader}")
    cluster.propose_through_leader({"op": "set", "key": "config/max_nodes", "value": 100})
    time.sleep(0.3)
    val = cluster.get_consensus_state("config/max_nodes")
    print(f"Consensus state: {val}")
    cluster.stop_all()
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
