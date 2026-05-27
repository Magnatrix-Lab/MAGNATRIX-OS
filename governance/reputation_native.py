#!/usr/bin/env python3
"""
reputation_native.py — MAGNATRIX-OS Governance Layer
Pure-Python Agent Reputation System: trust scoring (0-100), slashing,
weighted voting, decay, recovery. No external dependencies. Runnable standalone.

Architecture:
  BaseLayer   — ReputationScore, ReputationEvent, VoteRecord, AgentProfile
  CoreEngine  — ReputationEngine (scoring, slashing, decay, recovery)
  Features    — WeightedVoter, SlashingManager, DecayRecovery, ReputationOracle
  Kernel      — ReputationKernel bridge to MAGNATRIX Layer 8 (Governance)
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# BASELAYER — ReputationScore, ReputationEvent, VoteRecord, AgentProfile
# ═══════════════════════════════════════════════════════════════════════════════

class EventType(Enum):
    """Types of reputation-affecting events."""
    TASK_SUCCESS = auto()
    TASK_FAILURE = auto()
    BYZANTINE_ACT = auto()
    SLASH_PENALTY = auto()
    RECOVERY_BONUS = auto()
    CONSENSUS_PARTICIPATE = auto()
    CONSENSUS_VIOLATE = auto()
    HEARTBEAT_MISS = auto()
    HEARTBEAT_RESTORE = auto()
    HUMAN_OVERRIDE = auto()
    AUDIT_PASS = auto()
    AUDIT_FAIL = auto()


class AgentState(Enum):
    """Operational state of an agent in the reputation system."""
    ACTIVE = auto()
    SUSPENDED = auto()
    SLASHED = auto()
    RECOVERING = auto()
    EJECTED = auto()


@dataclass
class ReputationEvent:
    """A single reputation-affecting event for an agent."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    event_type: EventType = EventType.TASK_SUCCESS
    delta: float = 0.0          # Raw score delta (-100 to +100 typical)
    weight: float = 1.0         # Event importance multiplier
    timestamp: float = field(default_factory=time.time)
    reason: str = ""
    proof_hash: str = ""        # Hash of supporting evidence
    issuer: str = "system"      # Who issued this event

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "event_type": self.event_type.name,
            "delta": self.delta,
            "weight": self.weight,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "proof_hash": self.proof_hash,
            "issuer": self.issuer,
        }


@dataclass
class VoteRecord:
    """A single weighted vote in governance."""
    vote_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    voter_id: str = ""
    proposal_id: str = ""
    vote: int = 0               # -1 = against, 0 = abstain, +1 = for
    weight: float = 1.0         # Voting power (derived from reputation)
    timestamp: float = field(default_factory=time.time)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vote_id": self.vote_id,
            "voter_id": self.voter_id,
            "proposal_id": self.proposal_id,
            "vote": self.vote,
            "weight": self.weight,
            "timestamp": self.timestamp,
            "reason": self.reason,
        }


@dataclass
class ReputationScore:
    """Composite reputation score for an agent."""
    agent_id: str = ""
    overall: float = 50.0       # 0-100 primary score
    performance: float = 50.0   # Task success / reliability
    integrity: float = 50.0     # Byzantine / honesty
    participation: float = 50.0   # Consensus / heartbeat engagement
    last_updated: float = field(default_factory=time.time)
    history: deque = field(default_factory=lambda: deque(maxlen=500))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "overall": round(self.overall, 2),
            "performance": round(self.performance, 2),
            "integrity": round(self.integrity, 2),
            "participation": round(self.participation, 2),
            "last_updated": self.last_updated,
            "history_len": len(self.history),
        }


@dataclass
class AgentProfile:
    """Full reputation profile for an agent."""
    agent_id: str = ""
    name: str = ""
    public_key: str = ""
    state: AgentState = AgentState.ACTIVE
    score: ReputationScore = field(default_factory=ReputationScore)
    events: List[ReputationEvent] = field(default_factory=list)
    votes_cast: List[VoteRecord] = field(default_factory=list)
    slash_count: int = 0
    recovery_start: float = 0.0
    joined_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "public_key": self.public_key[:16] + "..." if len(self.public_key) > 16 else self.public_key,
            "state": self.state.name,
            "score": self.score.to_dict(),
            "events_count": len(self.events),
            "votes_cast": len(self.votes_cast),
            "slash_count": self.slash_count,
            "recovery_start": self.recovery_start,
            "joined_at": self.joined_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# COREENGINE — ReputationEngine (scoring, slashing, decay, recovery)
# ═══════════════════════════════════════════════════════════════════════════════

class ReputationEngine:
    """
    Core reputation scoring engine.
    Computes composite scores from events with configurable weights.
    """

    # Default event-type score deltas
    DEFAULT_DELTAS: Dict[EventType, float] = {
        EventType.TASK_SUCCESS: +3.0,
        EventType.TASK_FAILURE: -5.0,
        EventType.BYZANTINE_ACT: -25.0,
        EventType.SLASH_PENALTY: -15.0,
        EventType.RECOVERY_BONUS: +5.0,
        EventType.CONSENSUS_PARTICIPATE: +1.5,
        EventType.CONSENSUS_VIOLATE: -10.0,
        EventType.HEARTBEAT_MISS: -2.0,
        EventType.HEARTBEAT_RESTORE: +1.0,
        EventType.HUMAN_OVERRIDE: 0.0,
        EventType.AUDIT_PASS: +2.0,
        EventType.AUDIT_FAIL: -8.0,
    }

    # Score category mapping per event type
    CATEGORY_MAP: Dict[EventType, str] = {
        EventType.TASK_SUCCESS: "performance",
        EventType.TASK_FAILURE: "performance",
        EventType.BYZANTINE_ACT: "integrity",
        EventType.SLASH_PENALTY: "integrity",
        EventType.RECOVERY_BONUS: "integrity",
        EventType.CONSENSUS_PARTICIPATE: "participation",
        EventType.CONSENSUS_VIOLATE: "participation",
        EventType.HEARTBEAT_MISS: "participation",
        EventType.HEARTBEAT_RESTORE: "participation",
        EventType.HUMAN_OVERRIDE: "integrity",
        EventType.AUDIT_PASS: "performance",
        EventType.AUDIT_FAIL: "performance",
    }

    def __init__(
        self,
        decay_rate: float = 0.02,          # Per-hour decay factor
        recovery_rate: float = 0.5,        # Per-hour recovery boost
        slash_threshold: float = 20.0,     # Score below → slashed
        eject_threshold: float = 5.0,      # Score below → ejected
        probation_period: float = 3600.0,  # Seconds for recovery probation
    ) -> None:
        self.decay_rate = decay_rate
        self.recovery_rate = recovery_rate
        self.slash_threshold = slash_threshold
        self.eject_threshold = eject_threshold
        self.probation_period = probation_period
        self.agents: Dict[str, AgentProfile] = {}
        self.events_log: deque = deque(maxlen=5000)
        self.custom_deltas: Dict[EventType, float] = dict(self.DEFAULT_DELTAS)
        self._lock = False  # Cooperative mutex flag (no threading dep)

    # ── Registration ──

    def register(
        self,
        agent_id: str,
        name: str = "",
        public_key: str = "",
        initial_score: float = 50.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentProfile:
        """Register a new agent into the reputation system."""
        if agent_id in self.agents:
            raise ValueError(f"Agent {agent_id} already registered")
        profile = AgentProfile(
            agent_id=agent_id,
            name=name or agent_id,
            public_key=public_key,
            score=ReputationScore(
                agent_id=agent_id,
                overall=initial_score,
                performance=initial_score,
                integrity=initial_score,
                participation=initial_score,
            ),
            metadata=metadata or {},
        )
        self.agents[agent_id] = profile
        return profile

    def unregister(self, agent_id: str) -> None:
        """Remove an agent from the system."""
        self.agents.pop(agent_id, None)

    # ── Event Processing ──

    def emit(self, event: ReputationEvent) -> ReputationScore:
        """
        Process a reputation event and update the agent's score.
        Thread-safe via cooperative locking.
        """
        if self._lock:
            raise RuntimeError("ReputationEngine is locked")
        if event.agent_id not in self.agents:
            raise KeyError(f"Agent {event.agent_id} not registered")

        profile = self.agents[event.agent_id]
        base_delta = self.custom_deltas.get(event.event_type, 0.0)
        # Override with explicit delta if provided
        delta = event.delta if event.delta != 0.0 else base_delta
        delta *= event.weight

        # Apply to category
        category = self.CATEGORY_MAP.get(event.event_type, "overall")
        if category == "performance":
            profile.score.performance = max(0.0, min(100.0, profile.score.performance + delta))
        elif category == "integrity":
            profile.score.integrity = max(0.0, min(100.0, profile.score.integrity + delta))
        elif category == "participation":
            profile.score.participation = max(0.0, min(100.0, profile.score.participation + delta))

        # Recompute overall as weighted average
        profile.score.overall = self._compute_overall(profile.score)
        profile.score.last_updated = time.time()
        profile.score.history.append(event.to_dict())
        profile.events.append(event)
        self.events_log.append(event)

        # State transitions
        self._check_state_transition(profile)

        return profile.score

    def _compute_overall(self, score: ReputationScore) -> float:
        """Weighted composite of sub-scores."""
        # Performance 40%, Integrity 40%, Participation 20%
        return (
            score.performance * 0.40
            + score.integrity * 0.40
            + score.participation * 0.20
        )

    def _check_state_transition(self, profile: AgentProfile) -> None:
        """Check if agent state should change based on score."""
        score = profile.score.overall
        if score <= self.eject_threshold and profile.state != AgentState.EJECTED:
            profile.state = AgentState.EJECTED
            profile.slash_count += 1
        elif score <= self.slash_threshold and profile.state not in (AgentState.SLASHED, AgentState.EJECTED):
            profile.state = AgentState.SLASHED
            profile.slash_count += 1
        elif profile.state == AgentState.SLASHED and score > self.slash_threshold + 10:
            # Auto-recover if score rises sufficiently
            profile.state = AgentState.RECOVERING
            profile.recovery_start = time.time()
        elif profile.state == AgentState.RECOVERING:
            elapsed = time.time() - profile.recovery_start
            if elapsed >= self.probation_period and score > self.slash_threshold + 5:
                profile.state = AgentState.ACTIVE

    def batch_emit(self, events: List[ReputationEvent]) -> Dict[str, ReputationScore]:
        """Process multiple events atomically."""
        results: Dict[str, ReputationScore] = {}
        for ev in events:
            results[ev.agent_id] = self.emit(ev)
        return results

    # ── Decay ──

    def apply_decay(self, agent_id: Optional[str] = None) -> None:
        """
        Apply time-based reputation decay to all agents or a specific one.
        Decay reduces scores gradually to prevent stale high scores.
        """
        targets = [self.agents[agent_id]] if agent_id else list(self.agents.values())
        now = time.time()
        for profile in targets:
            hours_elapsed = (now - profile.score.last_updated) / 3600.0
            if hours_elapsed <= 0:
                continue
            decay = self.decay_rate * hours_elapsed
            # Decay affects all categories, but integrity decays slower
            profile.score.performance = max(0.0, profile.score.performance - decay)
            profile.score.integrity = max(0.0, profile.score.integrity - decay * 0.5)
            profile.score.participation = max(0.0, profile.score.participation - decay)
            profile.score.overall = self._compute_overall(profile.score)
            profile.score.last_updated = now
            self._check_state_transition(profile)

    # ── Recovery ──

    def apply_recovery(self, agent_id: str, bonus: float = 5.0) -> ReputationScore:
        """Manually trigger recovery boost for a recovering agent."""
        if agent_id not in self.agents:
            raise KeyError(agent_id)
        profile = self.agents[agent_id]
        if profile.state not in (AgentState.SLASHED, AgentState.RECOVERING):
            raise ValueError(f"Agent {agent_id} not in recoverable state")

        event = ReputationEvent(
            agent_id=agent_id,
            event_type=EventType.RECOVERY_BONUS,
            delta=bonus,
            reason="manual recovery boost",
            issuer="recovery_system",
        )
        return self.emit(event)

    # ── Queries ──

    def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        return self.agents.get(agent_id)

    def get_leaderboard(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """Return top-N agents by overall score."""
        ranked = sorted(
            self.agents.items(),
            key=lambda kv: kv[1].score.overall,
            reverse=True,
        )
        return [(aid, p.score.overall) for aid, p in ranked[:top_n]]

    def get_network_health(self) -> Dict[str, Any]:
        """Aggregate reputation health of the entire agent network."""
        if not self.agents:
            return {"status": "empty", "avg_score": 0.0}
        scores = [p.score.overall for p in self.agents.values()]
        states = defaultdict(int)
        for p in self.agents.values():
            states[p.state.name] += 1
        return {
            "status": "healthy" if min(scores) > 30 else "degraded" if min(scores) > 15 else "critical",
            "agent_count": len(scores),
            "avg_score": round(sum(scores) / len(scores), 2),
            "min_score": round(min(scores), 2),
            "max_score": round(max(scores), 2),
            "state_distribution": dict(states),
        }

    def export_snapshot(self) -> Dict[str, Any]:
        """Export full system state as dictionary."""
        return {
            "agents": {aid: p.to_dict() for aid, p in self.agents.items()},
            "events": [e.to_dict() for e in self.events_log],
            "config": {
                "decay_rate": self.decay_rate,
                "recovery_rate": self.recovery_rate,
                "slash_threshold": self.slash_threshold,
                "eject_threshold": self.eject_threshold,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURES — WeightedVoter, SlashingManager, DecayRecovery, ReputationOracle
# ═══════════════════════════════════════════════════════════════════════════════

class WeightedVoter:
    """
    Governance voting where vote weight is derived from reputation score.
    Prevents Sybil attacks by making influence costly (requires good reputation).
    """

    def __init__(self, engine: ReputationEngine, min_score_to_vote: float = 30.0) -> None:
        self.engine = engine
        self.min_score_to_vote = min_score_to_vote
        self.proposals: Dict[str, Dict[str, Any]] = {}  # proposal_id → metadata
        self.votes: Dict[str, List[VoteRecord]] = defaultdict(list)

    def create_proposal(self, proposal_id: str, title: str, quorum: float = 0.51) -> None:
        """Register a new governance proposal."""
        self.proposals[proposal_id] = {
            "title": title,
            "quorum": quorum,
            "created_at": time.time(),
            "closed_at": None,
            "result": None,
        }

    def cast_vote(self, voter_id: str, proposal_id: str, vote: int, reason: str = "") -> Optional[VoteRecord]:
        """
        Cast a weighted vote. Returns None if voter ineligible.
        vote: -1 = against, 0 = abstain, +1 = for
        """
        if proposal_id not in self.proposals:
            raise KeyError(f"Proposal {proposal_id} not found")
        profile = self.engine.get_profile(voter_id)
        if not profile:
            raise KeyError(f"Voter {voter_id} not registered")
        if profile.score.overall < self.min_score_to_vote:
            return None  # Ineligible
        if profile.state != AgentState.ACTIVE:
            return None  # Only active agents vote

        # Vote weight = reputation score / 100 * (1 + participation bonus)
        weight = (profile.score.overall / 100.0) * (1.0 + profile.score.participation / 200.0)
        record = VoteRecord(
            voter_id=voter_id,
            proposal_id=proposal_id,
            vote=vote,
            weight=round(weight, 4),
            reason=reason,
        )
        self.votes[proposal_id].append(record)
        profile.votes_cast.append(record)
        return record

    def tally(self, proposal_id: str) -> Dict[str, Any]:
        """Compute weighted vote results for a proposal."""
        if proposal_id not in self.proposals:
            raise KeyError(proposal_id)
        ballots = self.votes.get(proposal_id, [])
        total_weight = sum(v.weight for v in ballots if v.vote != 0)
        for_weight = sum(v.weight for v in ballots if v.vote == 1)
        against_weight = sum(v.weight for v in ballots if v.vote == -1)

        proposal = self.proposals[proposal_id]
        passed = False
        if total_weight > 0:
            passed = (for_weight / total_weight) >= proposal["quorum"]

        proposal["closed_at"] = time.time()
        proposal["result"] = "passed" if passed else "rejected"

        return {
            "proposal_id": proposal_id,
            "title": proposal["title"],
            "total_weight": round(total_weight, 4),
            "for_weight": round(for_weight, 4),
            "against_weight": round(against_weight, 4),
            "for_ratio": round(for_weight / total_weight, 4) if total_weight else 0.0,
            "quorum": proposal["quorum"],
            "passed": passed,
            "voter_count": len(ballots),
        }


class SlashingManager:
    """
    Graduated slashing with severity tiers, appeal window, and burn/redistribute.
    """

    SEVERITY_TIERS: Dict[str, Dict[str, Any]] = {
        "minor": {"score_penalty": -5.0, "slash_pct": 0.05, "cooldown": 300},
        "moderate": {"score_penalty": -15.0, "slash_pct": 0.15, "cooldown": 900},
        "severe": {"score_penalty": -35.0, "slash_pct": 0.50, "cooldown": 3600},
        "critical": {"score_penalty": -100.0, "slash_pct": 1.00, "cooldown": 86400},
    }

    def __init__(self, engine: ReputationEngine) -> None:
        self.engine = engine
        self.appeals: Dict[str, Dict[str, Any]] = {}  # event_id → appeal status
        self.appeal_window = 600  # Seconds to appeal

    def slash(self, agent_id: str, severity: str, reason: str, proof_hash: str = "") -> ReputationEvent:
        """Execute a slashing penalty against an agent."""
        tier = self.SEVERITY_TIERS.get(severity, self.SEVERITY_TIERS["moderate"])
        event = ReputationEvent(
            agent_id=agent_id,
            event_type=EventType.SLASH_PENALTY,
            delta=tier["score_penalty"],
            weight=tier["slash_pct"],
            reason=f"[{severity}] {reason}",
            proof_hash=proof_hash,
            issuer="slashing_manager",
        )
        self.engine.emit(event)
        profile = self.engine.get_profile(agent_id)
        if profile:
            profile.slash_count += 1
        self.appeals[event.event_id] = {
            "status": "pending",
            "deadline": time.time() + self.appeal_window,
            "severity": severity,
        }
        return event

    def appeal(self, event_id: str, evidence: str) -> bool:
        """Appeal a slash. If within window, mark for review."""
        if event_id not in self.appeals:
            return False
        info = self.appeals[event_id]
        if time.time() > info["deadline"]:
            info["status"] = "expired"
            return False
        info["status"] = "under_review"
        info["evidence"] = evidence
        return True

    def resolve_appeal(self, event_id: str, overturn: bool) -> bool:
        """Resolve an appeal. If overturned, partially restore score."""
        if event_id not in self.appeals:
            return False
        info = self.appeals[event_id]
        if info["status"] != "under_review":
            return False
        info["status"] = "overturned" if overturn else "upheld"
        if overturn:
            # Find the event and reverse 50% of penalty
            for ev in list(self.engine.events_log):
                if ev.event_id == event_id:
                    restore = ReputationEvent(
                        agent_id=ev.agent_id,
                        event_type=EventType.RECOVERY_BONUS,
                        delta=abs(ev.delta) * 0.5,
                        reason=f"appeal overturned for {event_id}",
                        issuer="slashing_manager",
                    )
                    self.engine.emit(restore)
                    break
        return True


class DecayRecovery:
    """
    Automated decay + recovery scheduler.
    Runs periodic decay on all agents and auto-recovery for eligible ones.
    """

    def __init__(self, engine: ReputationEngine) -> None:
        self.engine = engine
        self.last_decay_run: float = 0.0
        self.decay_interval: float = 3600.0  # Run decay every hour
        self.recovery_threshold: float = 25.0

    def tick(self) -> Dict[str, Any]:
        """Execute one decay/recovery cycle. Call periodically."""
        now = time.time()
        results: Dict[str, Any] = {"decayed": [], "recovered": []}
        if now - self.last_decay_run >= self.decay_interval:
            self.engine.apply_decay()
            self.last_decay_run = now
            results["decayed"] = list(self.engine.agents.keys())

        # Auto-recovery for recovering agents above threshold
        for aid, profile in self.engine.agents.items():
            if profile.state == AgentState.RECOVERING:
                if profile.score.overall >= self.recovery_threshold:
                    self.engine.apply_recovery(aid, bonus=2.0)
                    results["recovered"].append(aid)
        return results


class ReputationOracle:
    """
    External-facing reputation query service.
    Provides attestation, challenge-response, and score proofs.
    """

    def __init__(self, engine: ReputationEngine) -> None:
        self.engine = engine
        self.challenges: Dict[str, Dict[str, Any]] = {}

    def get_attestation(self, agent_id: str) -> Dict[str, Any]:
        """Produce a signed-like attestation of an agent's reputation."""
        profile = self.engine.get_profile(agent_id)
        if not profile:
            return {"valid": False, "reason": "agent not found"}
        # Simple hash-based proof (no crypto lib dependency)
        payload = json.dumps(profile.score.to_dict(), sort_keys=True)
        proof = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return {
            "valid": True,
            "agent_id": agent_id,
            "score": profile.score.to_dict(),
            "state": profile.state.name,
            "proof": proof,
            "timestamp": time.time(),
        }

    def challenge(self, agent_id: str) -> str:
        """Issue a reputation challenge to an agent."""
        challenge_id = str(uuid.uuid4())[:8]
        self.challenges[challenge_id] = {
            "agent_id": agent_id,
            "issued_at": time.time(),
            "resolved": False,
        }
        return challenge_id

    def verify(self, challenge_id: str, response: str) -> bool:
        """Verify a challenge response (simplified)."""
        if challenge_id not in self.challenges:
            return False
        self.challenges[challenge_id]["resolved"] = True
        # In production: verify cryptographic signature
        return len(response) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# KERNEL — ReputationKernel bridge to MAGNATRIX Layer 8 (Governance)
# ═══════════════════════════════════════════════════════════════════════════════

class ReputationKernel:
    """
    MAGNATRIX Governance Layer bridge.
    Integrates reputation system with the broader OS kernel.
    """

    def __init__(self) -> None:
        self.engine = ReputationEngine()
        self.voter = WeightedVoter(self.engine)
        self.slasher = SlashingManager(self.engine)
        self.decay_recovery = DecayRecovery(self.engine)
        self.oracle = ReputationOracle(self.engine)
        self.hooks: List[Callable[[str, EventType, float], None]] = []

    def register_hook(self, fn: Callable[[str, EventType, float], None]) -> None:
        """Register a callback for reputation events."""
        self.hooks.append(fn)

    def emit(self, event: ReputationEvent) -> ReputationScore:
        """Emit event through engine + propagate to hooks."""
        score = self.engine.emit(event)
        for fn in self.hooks:
            try:
                fn(event.agent_id, event.event_type, score.overall)
            except Exception:
                pass
        return score

    def onboard_agent(self, agent_id: str, **kwargs: Any) -> AgentProfile:
        """Register and bootstrap a new agent."""
        profile = self.engine.register(agent_id, **kwargs)
        # Emit bootstrap participation event
        self.emit(ReputationEvent(
            agent_id=agent_id,
            event_type=EventType.CONSENSUS_PARTICIPATE,
            delta=0.0,
            reason="agent onboarded",
        ))
        return profile

    def evaluate_task(self, agent_id: str, success: bool, metadata: Optional[Dict[str, Any]] = None) -> ReputationScore:
        """Evaluate agent task completion and update reputation."""
        event = ReputationEvent(
            agent_id=agent_id,
            event_type=EventType.TASK_SUCCESS if success else EventType.TASK_FAILURE,
            reason=metadata.get("reason", "") if metadata else "",
        )
        return self.emit(event)

    def governance_vote(self, voter_id: str, proposal_id: str, vote: int, reason: str = "") -> Optional[VoteRecord]:
        """Cast a reputation-weighted governance vote."""
        return self.voter.cast_vote(voter_id, proposal_id, vote, reason)

    def health(self) -> Dict[str, Any]:
        """System health report."""
        return {
            "reputation": self.engine.get_network_health(),
            "proposals_active": len(self.voter.proposals),
            "appeals_pending": sum(1 for a in self.slasher.appeals.values() if a["status"] == "pending"),
            "decay_last_run": self.decay_recovery.last_decay_run,
        }

    def full_report(self) -> str:
        """Human-readable system report."""
        health = self.health()
        lines = [
            "═" * 60,
            "  MAGNATRIX-OS — Reputation System Report",
            "═" * 60,
            f"  Agents:        {health['reputation']['agent_count']}",
            f"  Status:        {health['reputation']['status']}",
            f"  Avg Score:     {health['reputation']['avg_score']}",
            f"  Min Score:     {health['reputation']['min_score']}",
            f"  Active Proposals: {health['proposals_active']}",
            f"  Pending Appeals:  {health['appeals_pending']}",
            "─" * 60,
        ]
        # Leaderboard
        lb = self.engine.get_leaderboard(top_n=5)
        lines.append("  Leaderboard:")
        for rank, (aid, score) in enumerate(lb, 1):
            profile = self.engine.get_profile(aid)
            lines.append(f"    {rank}. {aid:<20} {score:>6.1f}  [{profile.state.name if profile else '?'}]")
        lines.append("═" * 60)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════════

def _demo() -> None:
    print("=" * 70)
    print("REPUTATION_NATIVE.PY — Demo Run")
    print("=" * 70)

    kernel = ReputationKernel()

    # Onboard agents
    for i in range(5):
        kernel.onboard_agent(
            agent_id=f"agent-{i:02d}",
            name=f"Worker-{i}",
            initial_score=50.0 + i * 5,
        )

    # Simulate events
    kernel.evaluate_task("agent-00", success=True, metadata={"reason": "batch processed"})
    kernel.evaluate_task("agent-00", success=True)
    kernel.evaluate_task("agent-01", success=False, metadata={"reason": "timeout"})
    kernel.evaluate_task("agent-02", success=True)
    kernel.evaluate_task("agent-03", success=True)
    kernel.evaluate_task("agent-04", success=False, metadata={"reason": "byzantine output"})

    # Slash agent-04 for byzantine behavior
    kernel.slasher.slash("agent-04", "severe", "produced conflicting consensus vote", proof_hash="0xdeadbeef")

    # Another failure for agent-01
    kernel.evaluate_task("agent-01", success=False, metadata={"reason": "crash"})
    kernel.engine.emit(ReputationEvent(
        agent_id="agent-01",
        event_type=EventType.BYZANTINE_ACT,
        delta=-25.0,
        reason="double-signed proposal",
    ))

    # Governance vote
    kernel.voter.create_proposal("prop-001", "Increase task timeout to 30s", quorum=0.6)
    kernel.governance_vote("agent-00", "prop-001", 1, "needed for slow tasks")
    kernel.governance_vote("agent-01", "prop-001", 1)
    kernel.governance_vote("agent-02", "prop-001", -1, "too lenient")
    kernel.governance_vote("agent-03", "prop-001", 1)
    tally = kernel.voter.tally("prop-001")

    # Decay cycle
    kernel.decay_recovery.tick()

    # Report
    print(kernel.full_report())

    print("\n📊 Proposal prop-001 Results:")
    for k, v in tally.items():
        print(f"   {k}: {v}")

    print("\n📋 Agent-04 Profile (post-slash):")
    p = kernel.engine.get_profile("agent-04")
    print(json.dumps(p.to_dict(), indent=2) if p else "   (ejected)")

    print("\n📋 Agent-01 State:")
    p = kernel.engine.get_profile("agent-01")
    print(f"   state={p.state.name}, score={p.score.overall:.1f}, slashes={p.slash_count}")

    print("\n✅ Demo complete.")


if __name__ == "__main__":
    _demo()
