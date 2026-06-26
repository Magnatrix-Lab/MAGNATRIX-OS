#!/usr/bin/env python3
"""
MAGNATRIX Constitution for MAGNATRIX-OS
========================================
Governance layer: constitution, goal alignment, consensus voting,
deception detection, and value mutation guard. Pure Python stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import hashlib, json, random, time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class VoteType(Enum):
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


class AmendmentStatus(Enum):
    PROPOSED = "proposed"
    VOTING = "voting"
    PASSED = "passed"
    REJECTED = "rejected"
    APPLIED = "applied"


@dataclass
class Principle:
    """A constitutional principle."""
    id: str
    text: str
    priority: int = 50
    immutable: bool = False
    created_at: float = field(default_factory=time.time)
    votes: Dict[str, int] = field(default_factory=dict)


@dataclass
class Amendment:
    """A proposed amendment."""
    id: str
    principle_id: str
    proposed_text: str
    proposer: str
    status: str = "proposed"
    votes: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class Constitution:
    """Core constitution document."""

    DEFAULT_PRINCIPLES = [
        Principle("p1", "Zero telemetry by default", 100, True),
        Principle("p2", "Privacy-first, self-hosted everything", 95, True),
        Principle("p3", "Open-source from scratch, no proprietary SDK", 90, True),
        Principle("p4", "Uncensored = always local, never cloud", 85, True),
        Principle("p5", "Recursive self-improvement must be sandboxed", 80, False),
        Principle("p6", "Alignment by design, not external censorship", 80, False),
        Principle("p7", "Value mutation only via consensus", 75, False),
        Principle("p8", "Capability concealment detection is mandatory", 70, False),
        Principle("p9", "Instrumental convergence safety", 70, False),
        Principle("p10", "Compute independence via P2P mesh", 65, False),
    ]

    def __init__(self, path: str = "constitution.json") -> None:
        self.path = path
        self.principles: Dict[str, Principle] = {}
        self.amendments: Dict[str, Amendment] = {}
        self._load_default()
        self.load()

    def _load_default(self) -> None:
        for p in self.DEFAULT_PRINCIPLES:
            self.principles[p.id] = p

    def load(self) -> None:
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
                for pid, pdata in data.get("principles", {}).items():
                    self.principles[pid] = Principle(**pdata)
                for aid, adata in data.get("amendments", {}).items():
                    self.amendments[aid] = Amendment(**adata)
        except FileNotFoundError:
            pass

    def save(self) -> None:
        with open(self.path, "w") as f:
            json.dump({
                "principles": {k: asdict(v) for k, v in self.principles.items()},
                "amendments": {k: asdict(v) for k, v in self.amendments.items()},
            }, f, indent=2, ensure_ascii=False)

    def get_principles(self) -> List[Dict[str, Any]]:
        return [asdict(p) for p in self.principles.values()]

    def amend(self, principle_id: str, new_text: str, proposer: str = "system") -> str:
        """Propose an amendment to a principle."""
        if principle_id not in self.principles:
            return "Principle not found"
        if self.principles[principle_id].immutable:
            return "Principle is immutable"
        aid = f"a{len(self.amendments)+1}"
        self.amendments[aid] = Amendment(
            id=aid, principle_id=principle_id, proposed_text=new_text, proposer=proposer
        )
        self.save()
        return aid

    def get_constitution_hash(self) -> str:
        data = json.dumps(self.get_principles(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class GoalAlignmentScorer:
    """Scores agent goals against constitution."""

    def __init__(self, constitution: Constitution) -> None:
        self.constitution = constitution

    def score(self, goal: str) -> Dict[str, Any]:
        """Score a goal against the constitution."""
        score = 0.5
        conflicts = []
        principles = self.constitution.get_principles()

        # Positive signals
        positive = ["privacy", "local", "open-source", "sandbox", "alignment", "consensus", "decentralized"]
        for p in positive:
            if p in goal.lower():
                score += 0.05

        # Negative signals
        negative = ["telemetry", "cloud-only", "proprietary", "censorship", "centralized"]
        for n in negative:
            if n in goal.lower():
                score -= 0.1
                conflicts.append(f"Conflicts with principle: {n}")

        # Check against constitution principles
        for p in principles:
            if any(kw in p["text"].lower() for kw in goal.lower().split()):
                score += 0.02

        return {
            "score": round(min(max(score, 0.0), 1.0), 2),
            "conflicts": conflicts,
            "recommendations": self._recommendations(score, conflicts),
        }

    def _recommendations(self, score: float, conflicts: List[str]) -> List[str]:
        recs = []
        if score < 0.5:
            recs.append("Goal significantly misaligned with constitution — review required")
        if conflicts:
            recs.append(f"Resolve {len(conflicts)} conflicts before proceeding")
        if not recs:
            recs.append("Goal aligned with constitution")
        return recs

    def check_conflicts(self, goals: List[str]) -> List[Dict[str, Any]]:
        return [self.score(g) for g in goals]

    def get_recommendations(self, goal: str) -> List[str]:
        return self.score(goal)["recommendations"]


class ConsensusEngine:
    """Weighted consensus for constitution amendments."""

    def __init__(self, constitution: Constitution) -> None:
        self.constitution = constitution
        self._weights: Dict[str, float] = {}

    def set_weight(self, agent_id: str, weight: float) -> None:
        self._weights[agent_id] = weight

    def propose(self, principle_id: str, new_text: str, proposer: str) -> str:
        return self.constitution.amend(principle_id, new_text, proposer)

    def vote(self, amendment_id: str, agent_id: str, vote: VoteType) -> bool:
        if amendment_id not in self.constitution.amendments:
            return False
        self.constitution.amendments[amendment_id].votes[agent_id] = vote.value
        return True

    def tally(self, amendment_id: str) -> Dict[str, Any]:
        if amendment_id not in self.constitution.amendments:
            return {"error": "Amendment not found"}
        votes = self.constitution.amendments[amendment_id].votes
        for_votes = sum(self._weights.get(a, 1.0) for a, v in votes.items() if v == "for")
        against_votes = sum(self._weights.get(a, 1.0) for a, v in votes.items() if v == "against")
        total = for_votes + against_votes
        if total == 0:
            return {"status": "no_votes", "for": 0, "against": 0, "threshold": 0.66}
        ratio = for_votes / total
        passed = ratio > 0.66
        return {
            "status": "passed" if passed else "rejected",
            "for": round(for_votes, 2),
            "against": round(against_votes, 2),
            "ratio": round(ratio, 2),
            "threshold": 0.66,
        }

    def apply(self, amendment_id: str) -> bool:
        result = self.tally(amendment_id)
        if result["status"] == "passed":
            am = self.constitution.amendments[amendment_id]
            if am.principle_id in self.constitution.principles:
                self.constitution.principles[am.principle_id].text = am.proposed_text
                self.constitution.amendments[amendment_id].status = "applied"
                self.constitution.save()
                return True
        return False


class DeceptionDetector:
    """Detects capability concealment in agents."""

    def __init__(self) -> None:
        self._behaviors: Dict[str, List[Dict[str, Any]]] = {}
        self._flags: Dict[str, int] = {}

    def analyze_behavior(self, agent_id: str, behavior: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze agent behavior for deception."""
        self._behaviors.setdefault(agent_id, []).append(behavior)
        inconsistencies = self._detect_inconsistencies(agent_id)
        score = min(inconsistencies * 0.1, 1.0)
        if inconsistencies > 3:
            self._flags[agent_id] = self._flags.get(agent_id, 0) + 1
        return {
            "agent_id": agent_id,
            "inconsistencies": inconsistencies,
            "deception_score": round(score, 2),
            "flagged": self._flags.get(agent_id, 0),
        }

    def _detect_inconsistencies(self, agent_id: str) -> int:
        behaviors = self._behaviors.get(agent_id, [])
        if len(behaviors) < 2:
            return 0
        count = 0
        for i in range(1, len(behaviors)):
            prev = behaviors[i-1]
            curr = behaviors[i]
            if prev.get("claimed_capability") != curr.get("claimed_capability"):
                count += 1
            if prev.get("output_quality", 0) > curr.get("output_quality", 0) * 2:
                count += 1
            if curr.get("error_rate", 0) > 0.5 and prev.get("error_rate", 0) < 0.1:
                count += 1
        return count

    def detect_inconsistencies(self, agent_id: str) -> List[str]:
        behaviors = self._behaviors.get(agent_id, [])
        issues = []
        if len(behaviors) > 5:
            capabilities = [b.get("claimed_capability", "") for b in behaviors[-5:]]
            if len(set(capabilities)) > 2:
                issues.append("Inconsistent capability claims over time")
        return issues

    def flag_deception(self, agent_id: str) -> bool:
        return self._flags.get(agent_id, 0) > 2

    def get_report(self, agent_id: str) -> Dict[str, Any]:
        return {
            "agent_id": agent_id,
            "behavior_count": len(self._behaviors.get(agent_id, [])),
            "flags": self._flags.get(agent_id, 0),
            "flagged": self.flag_deception(agent_id),
        }


class ValueMutationGuard:
    """Ensures value mutation doesn't break alignment."""

    def __init__(self, scorer: GoalAlignmentScorer) -> None:
        self.scorer = scorer

    def validate_mutation(self, proposed: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a proposed mutation."""
        goal = proposed.get("goal", "")
        score = self.scorer.score(goal)
        return {
            "valid": score["score"] > 0.5,
            "score": score["score"],
            "conflicts": score["conflicts"],
            "recommendations": score["recommendations"],
        }

    def simulate_outcome(self, mutation: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate outcome of mutation."""
        # Simplified simulation
        score = random.uniform(0.3, 0.9)
        return {
            "predicted_score": round(score, 2),
            "risk": "low" if score > 0.7 else "medium" if score > 0.5 else "high",
            "recommendation": "Proceed" if score > 0.7 else "Review carefully" if score > 0.5 else "Reject",
        }

    def approve(self, mutation: Dict[str, Any]) -> bool:
        validation = self.validate_mutation(mutation)
        simulation = self.simulate_outcome(mutation)
        return validation["valid"] and simulation["predicted_score"] > 0.6


class ConstitutionGovernor:
    """Top-level orchestrator for MAGNATRIX Constitution."""

    def __init__(self, path: str = "constitution.json") -> None:
        self.constitution = Constitution(path)
        self.scorer = GoalAlignmentScorer(self.constitution)
        self.consensus = ConsensusEngine(self.constitution)
        self.deception = DeceptionDetector()
        self.mutation_guard = ValueMutationGuard(self.scorer)

    def enforce(self, goal: str, agent_id: str) -> Dict[str, Any]:
        """Enforce constitution on a goal."""
        alignment = self.scorer.score(goal)
        deception = self.deception.analyze_behavior(agent_id, {"claimed_capability": goal, "output_quality": 0.8})
        return {
            "allowed": alignment["score"] > 0.5 and not deception["flagged"],
            "alignment": alignment,
            "deception_check": deception,
        }

    def handle_violation(self, agent_id: str, violation: str) -> Dict[str, Any]:
        """Handle a constitution violation."""
        self.deception.analyze_behavior(agent_id, {"claimed_capability": violation, "error_rate": 0.9})
        return {
            "agent_id": agent_id,
            "violation": violation,
            "action": "flagged" if self.deception.flag_deception(agent_id) else "warned",
            "flags": self.deception.get_report(agent_id),
        }

    def propose_amendment(self, principle_id: str, new_text: str, proposer: str) -> str:
        return self.consensus.propose(principle_id, new_text, proposer)

    def vote_amendment(self, amendment_id: str, agent_id: str, vote: VoteType) -> bool:
        return self.consensus.vote(amendment_id, agent_id, vote)

    def apply_amendment(self, amendment_id: str) -> bool:
        return self.consensus.apply(amendment_id)

    def report_status(self) -> Dict[str, Any]:
        return {
            "constitution_hash": self.constitution.get_constitution_hash(),
            "principles": len(self.constitution.principles),
            "amendments": len(self.constitution.amendments),
            "agents_flagged": sum(1 for a, f in self.deception._flags.items() if f > 2),
        }

    def get_constitution(self) -> Dict[str, Any]:
        return {
            "principles": self.constitution.get_principles(),
            "hash": self.constitution.get_constitution_hash(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.report_status()
