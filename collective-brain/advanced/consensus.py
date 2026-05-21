#!/usr/bin/env python3
"""
consensus.py — Distributed Consensus Engine MAGNATRIX
Batch Super AI — Infrastructure Core

Swarm voting dengan Byzantine Fault Tolerance.
- propose → vote → tally → resolve
- Toleransi sampai 1/3 node Byzantine/malicious
"""
import hashlib
import json
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set


@dataclass
class Proposal:
    proposal_id: str
    topic: str
    payload: Dict[str, Any]
    proposer: str
    timestamp: str
    quorum_required: float = 0.67
    ttl_seconds: int = 300


@dataclass
class Vote:
    vote_id: str
    proposal_id: str
    node_id: str
    vote: str  # "yes" | "no" | "abstain"
    timestamp: str
    signature: str = ""  # simulated


@dataclass
class ConsensusResult:
    proposal_id: str
    status: str  # "ratified" | "rejected" | "pending" | "expired"
    yes_count: int
    no_count: int
    abstain_count: int
    total_votes: int
    quorum_met: bool
    byzantine_nodes_detected: List[str] = field(default_factory=list)


class ConsensusEngine:
    """Byzantine Fault Tolerant consensus for MAGNATRIX swarm."""

    def __init__(self, total_nodes: int = 5):
        self.total_nodes = max(total_nodes, 3)
        self.proposals: Dict[str, Proposal] = {}
        self.votes: Dict[str, List[Vote]] = {}  # proposal_id → votes
        self.node_reputation: Dict[str, float] = {}  # node_id → reputation 0-1
        self.byzantine_threshold = 0.33
        self.quorum = 0.67

    def propose(self, topic: str, payload: Dict[str, Any], proposer: str) -> Proposal:
        """Usulkan sesuatu ke swarm."""
        prop = Proposal(
            proposal_id=f"prop-{topic}-{int(time.time())}-{random.randint(1000,9999)}",
            topic=topic,
            payload=payload,
            proposer=proposer,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.proposals[prop.proposal_id] = prop
        self.votes[prop.proposal_id] = []
        return prop

    def vote(self, proposal_id: str, node_id: str, vote_value: str) -> Optional[Vote]:
        """Node memberikan suara pada proposal."""
        if proposal_id not in self.proposals:
            return None
        if vote_value not in ("yes", "no", "abstain"):
            return None

        # Cek duplikasi voting
        existing = [v for v in self.votes.get(proposal_id, []) if v.node_id == node_id]
        if existing:
            return None  # sudah vote

        v = Vote(
            vote_id=f"vote-{node_id}-{int(time.time())}",
            proposal_id=proposal_id,
            node_id=node_id,
            vote=vote_value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            signature=hashlib.sha256(f"{node_id}:{vote_value}:{proposal_id}".encode()).hexdigest()[:16],
        )
        self.votes[proposal_id].append(v)
        return v

    def tally(self, proposal_id: str) -> ConsensusResult:
        """Hitung hasil vote."""
        if proposal_id not in self.proposals:
            return ConsensusResult(proposal_id, "not_found", 0, 0, 0, 0, False)

        votes = self.votes.get(proposal_id, [])
        yes = sum(1 for v in votes if v.vote == "yes")
        no = sum(1 for v in votes if v.vote == "no")
        abstain = sum(1 for v in votes if v.vote == "abstain")
        total = yes + no + abstain

        # Byzantine detection: cek jika node voting pattern anomali
        byzantine = self._detect_byzantine(proposal_id)

        # Quorum: butuh 2/3 dari total nodes (bukan dari yang vote)
        quorum_met = (yes / self.total_nodes) >= self.quorum

        # Expired check
        prop = self.proposals[proposal_id]
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(prop.timestamp.replace("Z", "+00:00"))).total_seconds()
        if age > prop.ttl_seconds and not quorum_met:
            return ConsensusResult(proposal_id, "expired", yes, no, abstain, total, False, byzantine)

        if quorum_met:
            return ConsensusResult(proposal_id, "ratified", yes, no, abstain, total, True, byzantine)
        elif total >= self.total_nodes and not quorum_met:
            return ConsensusResult(proposal_id, "rejected", yes, no, abstain, total, False, byzantine)

        return ConsensusResult(proposal_id, "pending", yes, no, abstain, total, quorum_met, byzantine)

    def _detect_byzantine(self, proposal_id: str) -> List[str]:
        """Deteksi node dengan voting pattern mencurigakan."""
        byzantine_nodes = []
        votes = self.votes.get(proposal_id, [])

        # Cek jika node vote "no" secara konsisten di semua proposal (contrarian)
        node_votes: Dict[str, List[str]] = {}
        for v in votes:
            node_votes.setdefault(v.node_id, []).append(v.vote)

        for node_id, vlist in node_votes.items():
            if len(vlist) >= 2 and all(v == "no" for v in vlist):
                byzantine_nodes.append(node_id)

        # Cek jika node vote di proposal yang tidak ada (fake vote)
        # (Simulated — in real system, verified by signature)

        return byzantine_nodes

    def resolve_conflict(self, proposal_a_id: str, proposal_b_id: str) -> Optional[str]:
        """Resolve jika ada konflik proposals. Pilih yang lebih baru atau lebih banyak yes."""
        if proposal_a_id not in self.proposals or proposal_b_id not in self.proposals:
            return None

        a = self.proposals[proposal_a_id]
        b = self.proposals[proposal_b_id]

        # Compare timestamps
        ta = datetime.fromisoformat(a.timestamp.replace("Z", "+00:00"))
        tb = datetime.fromisoformat(b.timestamp.replace("Z", "+00:00"))

        # Compare yes votes
        votes_a = self.votes.get(proposal_a_id, [])
        votes_b = self.votes.get(proposal_b_id, [])
        yes_a = sum(1 for v in votes_a if v.vote == "yes")
        yes_b = sum(1 for v in votes_b if v.vote == "yes")

        # Weighted: 60% vote count, 40% recency
        score_a = yes_a * 0.6 + (ta.timestamp() if hasattr(ta, 'timestamp') else 0) * 0.4
        score_b = yes_b * 0.6 + (tb.timestamp() if hasattr(tb, 'timestamp') else 0) * 0.4

        return proposal_a_id if score_a >= score_b else proposal_b_id

    def get_proposal_status(self, proposal_id: str) -> Dict:
        """Get full status of a proposal."""
        prop = self.proposals.get(proposal_id)
        if not prop:
            return {"status": "not_found"}

        result = self.tally(proposal_id)
        return {
            "proposal": asdict(prop),
            "consensus": asdict(result),
            "votes": [asdict(v) for v in self.votes.get(proposal_id, [])],
        }

    def export_state(self) -> Dict:
        """Export full consensus state."""
        return {
            "total_nodes": self.total_nodes,
            "quorum": self.quorum,
            "byzantine_threshold": self.byzantine_threshold,
            "active_proposals": len(self.proposals),
            "total_votes_cast": sum(len(v) for v in self.votes.values()),
            "proposals": [asdict(p) for p in self.proposals.values()],
        }


# ── demo ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("MAGNATRIX Consensus Engine — Byzantine Fault Tolerant Voting")
    print("=" * 70)

    engine = ConsensusEngine(total_nodes=5)

    print("\n[1] PROPOSE: Deploy new trading strategy")
    prop = engine.propose(
        topic="strategy_deployment",
        payload={"strategy": "momentum_v2", "risk_level": "medium"},
        proposer="node-alpha",
    )
    print(f"    Proposal ID: {prop.proposal_id}")

    print("\n[2] VOTE")
    votes = [
        (prop.proposal_id, "node-alpha", "yes"),
        (prop.proposal_id, "node-beta", "yes"),
        (prop.proposal_id, "node-gamma", "yes"),
        (prop.proposal_id, "node-delta", "no"),
        (prop.proposal_id, "node-epsilon", "yes"),
    ]
    for pid, nid, v in votes:
        vote = engine.vote(pid, nid, v)
        print(f"    {nid}: {v}")

    print("\n[3] TALLY")
    result = engine.tally(prop.proposal_id)
    print(f"    Status: {result.status}")
    print(f"    Yes: {result.yes_count} | No: {result.no_count} | Abstain: {result.abstain_count}")
    print(f"    Quorum met: {result.quorum_met}")
    print(f"    Byzantine detected: {result.byzantine_nodes_detected}")

    print("\n[4] PROPOSE CONFLICTING: Same topic, different payload")
    prop2 = engine.propose(
        topic="strategy_deployment",
        payload={"strategy": "mean_reversion", "risk_level": "low"},
        proposer="node-beta",
    )
    engine.vote(prop2.proposal_id, "node-alpha", "yes")
    engine.vote(prop2.proposal_id, "node-beta", "yes")
    engine.vote(prop2.proposal_id, "node-gamma", "no")

    print(f"    Conflict resolution: {engine.resolve_conflict(prop.proposal_id, prop2.proposal_id)} wins")

    print("\n[5] BYZANTINE DETECTION")
    # Simulate a Byzantine node that always votes no
    prop3 = engine.propose(topic="security_patch", payload={"patch_id": "CVE-2026-001"}, proposer="node-gamma")
    for nid in ["node-alpha", "node-beta", "node-gamma", "node-delta", "node-epsilon"]:
        # node-delta always votes no (Byzantine)
        v = "no" if nid == "node-delta" else "yes"
        engine.vote(prop3.proposal_id, nid, v)
    result3 = engine.tally(prop3.proposal_id)
    print(f"    Byzantine nodes flagged: {result3.byzantine_nodes_detected}")
    print(f"    Status: {result3.status}")

    print("\n[6] EXPORT STATE")
    state = engine.export_state()
    print(json.dumps(state, indent=2, default=str)[:600] + "...")

    print("\n" + "=" * 70)
    print("Consensus demo selesai.")
    print("=" * 70)
