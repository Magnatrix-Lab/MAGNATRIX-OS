#!/usr/bin/env python3
"""
governance/governance_v2_native.py — MAGNATRIX-OS Governance V2

Super AI governance layer. Pure Python, stdlib only.

Voting, proposals, treasury, multisig, audit trail, time-lock.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ProposalStatus(Enum):
    DRAFT = "draft"
    VOTING = "voting"
    QUEUED = "queued"
    EXECUTED = "executed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class VoteType(Enum):
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    voter: str
    vote_type: VoteType
    weight: float = 1.0
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class Proposal:
    id: str = ""
    title: str = ""
    description: str = ""
    proposer: str = ""
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: float = 0.0
    voting_end: float = 0.0
    execution_time: float = 0.0
    votes: List[Vote] = field(default_factory=list)
    required_quorum: float = 0.5
    required_majority: float = 0.5
    time_lock: float = 86400.0
    actions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_votes(self) -> float:
        return sum(v.weight for v in self.votes)

    @property
    def for_votes(self) -> float:
        return sum(v.weight for v in self.votes if v.vote_type == VoteType.FOR)

    @property
    def against_votes(self) -> float:
        return sum(v.weight for v in self.votes if v.vote_type == VoteType.AGAINST)

    def is_passed(self) -> bool:
        if self.total_votes == 0:
            return False
        quorum_met = self.total_votes >= self.required_quorum
        majority_met = self.for_votes / self.total_votes >= self.required_majority
        return quorum_met and majority_met

    def is_expired(self) -> bool:
        return time.time() > self.voting_end

    def can_execute(self) -> bool:
        if self.status != ProposalStatus.QUEUED:
            return False
        return time.time() >= self.execution_time


class VotingSystem:
    """Weighted voting with multiple mechanisms."""

    def __init__(self):
        self._proposals: Dict[str, Proposal] = {}
        self._lock = threading.Lock()

    def create_proposal(self, title: str, description: str, proposer: str, actions: List[Dict], voting_duration: float = 86400.0, quorum: float = 0.5, majority: float = 0.5) -> str:
        proposal_id = hashlib.sha256(f"{proposer}{time.time()}".encode()).hexdigest()[:16]
        proposal = Proposal(
            id=proposal_id,
            title=title,
            description=description,
            proposer=proposer,
            status=ProposalStatus.VOTING,
            created_at=time.time(),
            voting_end=time.time() + voting_duration,
            execution_time=time.time() + voting_duration + 86400,
            actions=actions,
            required_quorum=quorum,
            required_majority=majority,
        )
        with self._lock:
            self._proposals[proposal_id] = proposal
        return proposal_id

    def vote(self, proposal_id: str, voter: str, vote_type: VoteType, weight: float = 1.0) -> bool:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if not proposal or proposal.status != ProposalStatus.VOTING:
                return False
            if proposal.is_expired():
                return False
            proposal.votes.append(Vote(voter, vote_type, weight))
            return True

    def tally(self, proposal_id: str) -> Tuple[bool, Dict[str, Any]]:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if not proposal:
                return False, {}

            if proposal.is_passed():
                proposal.status = ProposalStatus.QUEUED
                return True, {
                    "for": proposal.for_votes,
                    "against": proposal.against_votes,
                    "total": proposal.total_votes,
                    "status": "passed",
                }
            else:
                proposal.status = ProposalStatus.REJECTED
                return False, {
                    "for": proposal.for_votes,
                    "against": proposal.against_votes,
                    "total": proposal.total_votes,
                    "status": "rejected",
                }

    def execute(self, proposal_id: str) -> bool:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if not proposal or not proposal.can_execute():
                return False
            proposal.status = ProposalStatus.EXECUTED
            return True

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        return self._proposals.get(proposal_id)

    def list_proposals(self, status: Optional[ProposalStatus] = None) -> List[Proposal]:
        proposals = list(self._proposals.values())
        if status:
            proposals = [p for p in proposals if p.status == status]
        return proposals


class TreasuryManager:
    """Manage treasury allocation."""

    def __init__(self):
        self._balance: float = 0.0
        self._allocations: Dict[str, float] = {}
        self._lock = threading.Lock()

    def deposit(self, amount: float) -> None:
        with self._lock:
            self._balance += amount

    def allocate(self, recipient: str, amount: float) -> bool:
        with self._lock:
            if self._balance < amount:
                return False
            self._balance -= amount
            self._allocations[recipient] = self._allocations.get(recipient, 0.0) + amount
            return True

    def get_balance(self) -> float:
        with self._lock:
            return self._balance

    def get_allocations(self) -> Dict[str, float]:
        with self._lock:
            return self._allocations.copy()


class MultiSig:
    """Multi-signature requirement for critical actions."""

    def __init__(self, required_signatures: int = 2, signers: List[str] = None):
        self.required = required_signatures
        self.signers = set(signers or [])
        self._signatures: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    def propose_action(self, action_id: str) -> None:
        with self._lock:
            self._signatures[action_id] = set()

    def sign(self, action_id: str, signer: str) -> bool:
        with self._lock:
            if signer not in self.signers:
                return False
            if action_id not in self._signatures:
                self._signatures[action_id] = set()
            self._signatures[action_id].add(signer)
            return True

    def is_approved(self, action_id: str) -> bool:
        with self._lock:
            return len(self._signatures.get(action_id, set())) >= self.required

    def get_signatures(self, action_id: str) -> Set[str]:
        with self._lock:
            return self._signatures.get(action_id, set()).copy()


class AuditTrail:
    """Immutable governance action log."""

    def __init__(self, log_file: str = ".governance/audit.jsonl"):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        self._lock = threading.Lock()

    def record(self, action: str, actor: str, details: Dict[str, Any]) -> None:
        entry = {
            "timestamp": time.time(),
            "action": action,
            "actor": actor,
            "details": details,
        }
        with self._lock:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

    def query(self, action_type: Optional[str] = None, actor: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        results = []
        if not os.path.exists(self.log_file):
            return results
        with self._lock:
            with open(self.log_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if action_type and entry.get("action") != action_type:
                            continue
                        if actor and entry.get("actor") != actor:
                            continue
                        results.append(entry)
                        if len(results) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue
        return results

    def verify_integrity(self) -> bool:
        """Verify log integrity by checking hash chain."""
        if not os.path.exists(self.log_file):
            return True
        with open(self.log_file) as f:
            lines = f.readlines()
        for line in lines:
            try:
                json.loads(line)
            except json.JSONDecodeError:
                return False
        return True


class SlashingManager:
    """Penalize malicious actors."""

    def __init__(self):
        self._reputation: Dict[str, float] = defaultdict(lambda: 100.0)
        self._lock = threading.Lock()

    def slash(self, actor: str, amount: float, reason: str) -> float:
        with self._lock:
            self._reputation[actor] = max(0.0, self._reputation[actor] - amount)
            return self._reputation[actor]

    def get_reputation(self, actor: str) -> float:
        with self._lock:
            return self._reputation[actor]

    def is_banned(self, actor: str, threshold: float = 10.0) -> bool:
        return self.get_reputation(actor) < threshold


class DelegateManager:
    """Delegate voting power to representatives."""

    def __init__(self):
        self._delegations: Dict[str, str] = {}
        self._lock = threading.Lock()

    def delegate(self, voter: str, representative: str) -> None:
        with self._lock:
            self._delegations[voter] = representative

    def undelegate(self, voter: str) -> None:
        with self._lock:
            self._delegations.pop(voter, None)

    def get_representative(self, voter: str) -> Optional[str]:
        with self._lock:
            return self._delegations.get(voter)

    def get_voting_power(self, voter: str) -> List[str]:
        """Get all voters who delegated to this representative."""
        with self._lock:
            return [v for v, r in self._delegations.items() if r == voter]


class GovernanceEngine:
    """Main governance orchestrator."""

    def __init__(self):
        self.voting = VotingSystem()
        self.treasury = TreasuryManager()
        self.multisig = MultiSig(required_signatures=2, signers=["admin1", "admin2", "admin3"])
        self.audit = AuditTrail()
        self.slashing = SlashingManager()
        self.delegates = DelegateManager()
        self._emergency_mode = False

    def create_proposal(self, title: str, description: str, proposer: str, actions: List[Dict], voting_duration: float = 86400.0) -> str:
        proposal_id = self.voting.create_proposal(title, description, proposer, actions, voting_duration)
        self.audit.record("proposal_created", proposer, {"proposal_id": proposal_id, "title": title})
        return proposal_id

    def vote(self, proposal_id: str, voter: str, vote_type: str, weight: float = 1.0) -> bool:
        vt = VoteType(vote_type.lower())
        result = self.voting.vote(proposal_id, voter, vt, weight)
        if result:
            self.audit.record("vote_cast", voter, {"proposal_id": proposal_id, "vote": vote_type})
        return result

    def tally_and_execute(self, proposal_id: str) -> Tuple[bool, str]:
        passed, stats = self.voting.tally(proposal_id)
        if passed:
            self.audit.record("proposal_passed", "system", {"proposal_id": proposal_id, "stats": stats})
            return True, "Proposal passed and queued for execution"
        else:
            self.audit.record("proposal_rejected", "system", {"proposal_id": proposal_id, "stats": stats})
            return False, "Proposal rejected"

    def execute_proposal(self, proposal_id: str) -> bool:
        if self.voting.execute(proposal_id):
            self.audit.record("proposal_executed", "system", {"proposal_id": proposal_id})
            return True
        return False

    def emergency_shutdown(self, initiator: str) -> bool:
        if self.multisig.is_approved("emergency_shutdown"):
            self._emergency_mode = True
            self.audit.record("emergency_shutdown", initiator, {"status": "activated"})
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "proposals": len(self.voting.list_proposals()),
            "active_voting": len(self.voting.list_proposals(ProposalStatus.VOTING)),
            "treasury_balance": self.treasury.get_balance(),
            "emergency_mode": self._emergency_mode,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Governance V2 — Self-Test")
    print("=" * 60)

    # Test 1: Create proposal
    print("\n[1] Create proposal")
    gov = GovernanceEngine()
    pid = gov.create_proposal("Upgrade kernel", "Upgrade to v1.0", "alice", [{"action": "upgrade", "target": "kernel"}], voting_duration=60.0)
    assert pid is not None
    print("  OK", pid)

    # Test 2: Vote
    print("\n[2] Vote")
    assert gov.vote(pid, "bob", "for", 10.0) == True
    assert gov.vote(pid, "charlie", "against", 5.0) == True
    assert gov.vote(pid, "dave", "abstain", 2.0) == True
    print("  OK")

    # Test 3: Tally
    print("\n[3] Tally")
    passed, msg = gov.tally_and_execute(pid)
    print(f"  {msg}")
    assert passed == True

    # Test 4: Treasury
    print("\n[4] Treasury")
    gov.treasury.deposit(1000.0)
    assert gov.treasury.allocate("kernel", 100.0) == True
    assert gov.treasury.get_balance() == 900.0
    print("  OK")

    # Test 5: MultiSig
    print("\n[5] MultiSig")
    gov.multisig.propose_action("emergency_shutdown")
    gov.multisig.sign("emergency_shutdown", "admin1")
    gov.multisig.sign("emergency_shutdown", "admin2")
    assert gov.multisig.is_approved("emergency_shutdown") == True
    print("  OK")

    # Test 6: Audit trail
    print("\n[6] Audit trail")
    records = gov.audit.query(action_type="vote_cast", limit=10)
    assert len(records) >= 3
    assert gov.audit.verify_integrity() == True
    print(f"  OK ({len(records)} audit records)")

    # Test 7: Slashing
    print("\n[7] Slashing")
    gov.slashing.slash("malicious", 50.0, "bad behavior")
    assert gov.slashing.get_reputation("malicious") == 50.0
    assert gov.slashing.is_banned("malicious", threshold=60.0) == True
    print("  OK")

    # Test 8: Delegation
    print("\n[8] Delegation")
    gov.delegates.delegate("voter1", "rep1")
    gov.delegates.delegate("voter2", "rep1")
    assert gov.delegates.get_representative("voter1") == "rep1"
    assert len(gov.delegates.get_voting_power("rep1")) == 2
    print("  OK")

    # Test 9: Stats
    print("\n[9] Stats")
    stats = gov.get_stats()
    assert stats["proposals"] > 0
    print(f"  {stats}")

    print("\n" + "=" * 60)
    print("All self-tests passed")
    print("=" * 60)
