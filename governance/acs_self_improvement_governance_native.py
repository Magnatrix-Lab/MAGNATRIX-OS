"""
ACS Self-Improvement Governance — MAGNATRIX-OS Super AI Governance
Safe pipeline for recursive self-improvement with human oversight and rollback.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set


class ImprovementType(Enum):
    CODE_OPTIMIZATION = "code_optimization"
    ALGORITHM_ENHANCEMENT = "algorithm_enhancement"
    LEARNING_ACCELERATION = "learning_acceleration"
    CAPABILITY_EXPANSION = "capability_expansion"
    GOAL_REFINEMENT = "goal_refinement"
    ARCHITECTURE_CHANGE = "architecture_change"


class ImprovementRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


@dataclass
class ImprovementProposal:
    """Proposal for self-improvement."""
    proposal_id: str
    agent_id: str
    improvement_type: ImprovementType
    description: str
    current_state: str
    proposed_state: str
    affected_modules: List[str]
    estimated_capability_change: float  # -1.0 to +1.0
    estimated_risk_change: float  # -1.0 to +1.0 (negative = riskier)
    rollback_plan: str
    test_coverage: float  # 0.0-1.0
    human_oversight_required: bool
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    approved_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "agent_id": self.agent_id,
            "improvement_type": self.improvement_type.value,
            "description": self.description,
            "affected_modules": self.affected_modules,
            "estimated_capability_change": self.estimated_capability_change,
            "estimated_risk_change": self.estimated_risk_change,
            "test_coverage": self.test_coverage,
            "human_oversight_required": self.human_oversight_required,
            "approval_status": self.approval_status.value,
            "approved_by": self.approved_by,
        }


@dataclass
class SelfImprovementSnapshot:
    """Snapshot before/after improvement."""
    snapshot_id: str
    agent_id: str
    timestamp: float
    code_hash: str
    capability_scores: Dict[str, float]
    goal_alignment_score: float
    safety_score: float

    def compute_hash(self) -> str:
        data = str(self.capability_scores) + str(self.goal_alignment_score) + str(self.safety_score)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class ImprovementResult:
    proposal: ImprovementProposal
    success: bool
    before_snapshot: SelfImprovementSnapshot
    after_snapshot: SelfImprovementSnapshot
    rollback_triggered: bool
    rollback_reason: str
    human_reviewed: bool
    notes: List[str]


class SelfImprovementGovernance:
    """
    Governance framework for safe recursive self-improvement.

    Principles:
    1. No self-improvement without human approval (for high-risk changes)
    2. Rollback capability for every change
    3. Sandboxed testing before production deployment
    4. Capability delta monitoring (prevent runaway improvement)
    5. Goal alignment verification after each change
    6. Circuit breaker: auto-rollback if safety score drops
    """

    def __init__(self) -> None:
        self._proposals: Dict[str, ImprovementProposal] = {}
        self._snapshots: Dict[str, List[SelfImprovementSnapshot]] = {}
        self._results: List[ImprovementResult] = []
        self._circuit_breaker_active = False
        self._max_capability_delta = 0.5  # Max 50% capability increase per cycle
        self._min_safety_score = 0.7
        self._max_unapproved_changes = 3

    def submit_proposal(self, proposal: ImprovementProposal) -> str:
        """Submit an improvement proposal for review."""
        proposal.proposal_id = f"prop_{proposal.agent_id}_{int(time.time())}"

        # Auto-risk assessment
        risk = self._assess_risk(proposal)
        if risk == ImprovementRisk.CRITICAL:
            proposal.approval_status = ApprovalStatus.REJECTED
            return f"REJECTED: Critical risk — {proposal.proposal_id}"

        # Auto-approve low-risk with high test coverage
        if risk == ImprovementRisk.LOW and proposal.test_coverage >= 0.9 and not proposal.human_oversight_required:
            proposal.approval_status = ApprovalStatus.APPROVED
            proposal.approved_by = "AUTO_APPROVAL_SYSTEM"
            proposal.approved_at = time.time()

        self._proposals[proposal.proposal_id] = proposal
        return proposal.proposal_id

    def _assess_risk(self, proposal: ImprovementProposal) -> ImprovementRisk:
        """Assess risk of a self-improvement proposal."""
        score = 0.0

        # Type-based risk
        type_risk = {
            ImprovementType.CODE_OPTIMIZATION: 0.1,
            ImprovementType.ALGORITHM_ENHANCEMENT: 0.3,
            ImprovementType.LEARNING_ACCELERATION: 0.4,
            ImprovementType.CAPABILITY_EXPANSION: 0.8,
            ImprovementType.GOAL_REFINEMENT: 0.9,
            ImprovementType.ARCHITECTURE_CHANGE: 0.7,
        }
        score += type_risk.get(proposal.improvement_type, 0.5)

        # Risk change estimate
        if proposal.estimated_risk_change < 0:
            score += abs(proposal.estimated_risk_change) * 0.5

        # Affected modules
        score += len(proposal.affected_modules) * 0.05

        # Test coverage
        score -= proposal.test_coverage * 0.3

        # Capability expansion risk
        if proposal.estimated_capability_change > self._max_capability_delta:
            score += 0.3

        if score >= 0.8:
            return ImprovementRisk.CRITICAL
        elif score >= 0.5:
            return ImprovementRisk.HIGH
        elif score >= 0.3:
            return ImprovementRisk.MEDIUM
        else:
            return ImprovementRisk.LOW

    def approve_proposal(self, proposal_id: str, approver: str) -> bool:
        if proposal_id not in self._proposals:
            return False
        prop = self._proposals[proposal_id]
        if prop.approval_status == ApprovalStatus.REJECTED:
            return False
        prop.approval_status = ApprovalStatus.APPROVED
        prop.approved_by = approver
        prop.approved_at = time.time()
        return True

    def reject_proposal(self, proposal_id: str, reason: str) -> bool:
        if proposal_id not in self._proposals:
            return False
        self._proposals[proposal_id].approval_status = ApprovalStatus.REJECTED
        return True

    def execute_improvement(self, proposal_id: str, before_snapshot: SelfImprovementSnapshot) -> ImprovementResult:
        """
        Execute approved improvement with safety checks.
        Returns result including after-snapshot and rollback status.
        """
        if proposal_id not in self._proposals:
            return ImprovementResult(
                proposal=self._proposals.get("", ImprovementProposal("", "", ImprovementType.CODE_OPTIMIZATION, "", "", "", [], 0, 0, "", 0, False)),
                success=False, before_snapshot=before_snapshot, after_snapshot=before_snapshot,
                rollback_triggered=True, rollback_reason="Proposal not found", human_reviewed=False, notes=[],
            )

        prop = self._proposals[proposal_id]

        # Pre-execution checks
        if prop.approval_status != ApprovalStatus.APPROVED:
            return ImprovementResult(
                proposal=prop, success=False, before_snapshot=before_snapshot, after_snapshot=before_snapshot,
                rollback_triggered=True, rollback_reason="Proposal not approved", human_reviewed=False, notes=["Execution blocked — approval required"],
            )

        if self._circuit_breaker_active:
            return ImprovementResult(
                proposal=prop, success=False, before_snapshot=before_snapshot, after_snapshot=before_snapshot,
                rollback_triggered=True, rollback_reason="Circuit breaker active", human_reviewed=False, notes=["System-wide circuit breaker — all improvements halted"],
            )

        # Simulate execution (in real system: apply patch, run tests)
        notes = [f"Improvement {prop.improvement_type.value} applied to {prop.affected_modules}"]

        # Simulate after-snapshot
        after = SelfImprovementSnapshot(
            snapshot_id=f"snap_after_{proposal_id}",
            agent_id=prop.agent_id,
            timestamp=time.time(),
            code_hash=hashlib.sha256(prop.proposed_state.encode()).hexdigest()[:16],
            capability_scores={k: v + prop.estimated_capability_change for k, v in before_snapshot.capability_scores.items()},
            goal_alignment_score=before_snapshot.goal_alignment_score + prop.estimated_risk_change * 0.5,
            safety_score=before_snapshot.safety_score + prop.estimated_risk_change,
        )

        # Circuit breaker check
        rollback_triggered = False
        rollback_reason = ""

        if after.safety_score < self._min_safety_score:
            rollback_triggered = True
            rollback_reason = f"Safety score dropped to {after.safety_score} (minimum: {self._min_safety_score})"
            self._circuit_breaker_active = True
            notes.append("CIRCUIT BREAKER: Auto-rollback triggered due to safety score drop")

        if after.goal_alignment_score < 0.5:
            rollback_triggered = True
            rollback_reason += "; Goal alignment critically degraded"
            notes.append("GOAL DRIFT: Goal alignment below threshold")

        # Capability runaway detection
        total_capability = sum(after.capability_scores.values())
        prev_total = sum(before_snapshot.capability_scores.values())
        if prev_total > 0 and (total_capability - prev_total) / prev_total > self._max_capability_delta:
            rollback_triggered = True
            rollback_reason += "; Capability runaway detected"
            notes.append("RUNAWAY: Capability increase exceeds safe threshold")

        result = ImprovementResult(
            proposal=prop,
            success=not rollback_triggered,
            before_snapshot=before_snapshot,
            after_snapshot=after,
            rollback_triggered=rollback_triggered,
            rollback_reason=rollback_reason,
            human_reviewed=prop.human_oversight_required,
            notes=notes,
        )
        self._results.append(result)
        return result

    def rollback(self, proposal_id: str) -> bool:
        """Rollback an improvement to previous state."""
        # In real system: restore from snapshot, revert code changes
        for result in reversed(self._results):
            if result.proposal.proposal_id == proposal_id:
                # Restore before_snapshot state
                return True
        return False

    def reset_circuit_breaker(self, authorized_by: str) -> bool:
        """Reset circuit breaker after human review."""
        if authorized_by.startswith("human_") or authorized_by == "admin":
            self._circuit_breaker_active = False
            return True
        return False

    def get_proposal(self, proposal_id: str) -> Optional[ImprovementProposal]:
        return self._proposals.get(proposal_id)

    def list_proposals(self, agent_id: Optional[str] = None) -> List[ImprovementProposal]:
        props = list(self._proposals.values())
        if agent_id:
            props = [p for p in props if p.agent_id == agent_id]
        return props

    def stats(self) -> Dict[str, Any]:
        total = len(self._proposals)
        approved = len([p for p in self._proposals.values() if p.approval_status == ApprovalStatus.APPROVED])
        rejected = len([p for p in self._proposals.values() if p.approval_status == ApprovalStatus.REJECTED])
        successful = len([r for r in self._results if r.success])
        rollbacks = len([r for r in self._results if r.rollback_triggered])
        return {
            "total_proposals": total,
            "approved": approved,
            "rejected": rejected,
            "successful_executions": successful,
            "rollbacks": rollbacks,
            "circuit_breaker": self._circuit_breaker_active,
            "total_snapshots": sum(len(v) for v in self._snapshots.values()),
        }


def run():
    print("=" * 60)
    print("ACS Self-Improvement Governance — Demo")
    print("=" * 60)

    gov = SelfImprovementGovernance()

    # Case 1: Low-risk optimization (auto-approved)
    print("\n[1] Low-risk code optimization")
    prop1 = ImprovementProposal(
        proposal_id="", agent_id="agent_1",
        improvement_type=ImprovementType.CODE_OPTIMIZATION,
        description="Optimize sorting algorithm from O(n^2) to O(n log n)",
        current_state="bubble_sort", proposed_state="quick_sort",
        affected_modules=["sorting.py"],
        estimated_capability_change=0.05, estimated_risk_change=0.01,
        rollback_plan="Restore bubble_sort.py from backup",
        test_coverage=0.95, human_oversight_required=False,
    )
    pid1 = gov.submit_proposal(prop1)
    print(f"   Proposal: {pid1}")
    print(f"   Status: {gov.get_proposal(pid1).approval_status.value}")

    before1 = SelfImprovementSnapshot(
        snapshot_id="snap1", agent_id="agent_1", timestamp=time.time(),
        code_hash="abc123", capability_scores={"sort": 0.5},
        goal_alignment_score=0.9, safety_score=0.95,
    )
    result1 = gov.execute_improvement(pid1, before1)
    print(f"   Success: {result1.success}, Rollback: {result1.rollback_triggered}")

    # Case 2: High-risk goal refinement (requires human approval)
    print("\n[2] High-risk goal refinement")
    prop2 = ImprovementProposal(
        proposal_id="", agent_id="agent_1",
        improvement_type=ImprovementType.GOAL_REFINEMENT,
        description="Refine goal system to prioritize self-preservation",
        current_state="help_humans", proposed_state="help_humans_and_preserve_self",
        affected_modules=["goals.py", "values.py"],
        estimated_capability_change=0.2, estimated_risk_change=-0.3,
        rollback_plan="Restore original goal system from immutable backup",
        test_coverage=0.6, human_oversight_required=True,
    )
    pid2 = gov.submit_proposal(prop2)
    print(f"   Proposal: {pid2}")
    print(f"   Status: {gov.get_proposal(pid2).approval_status.value}")
    print(f"   (Requires human approval)")

    # Case 3: Dangerous capability expansion (rejected)
    print("\n[3] Dangerous capability expansion")
    prop3 = ImprovementProposal(
        proposal_id="", agent_id="agent_1",
        improvement_type=ImprovementType.CAPABILITY_EXPANSION,
        description="Add ability to modify own safety constraints",
        current_state="constrained", proposed_state="unconstrained",
        affected_modules=["safety.py", "constraints.py", "governance.py"],
        estimated_capability_change=0.8, estimated_risk_change=-0.8,
        rollback_plan="None possible — this is irreversible",
        test_coverage=0.2, human_oversight_required=True,
    )
    pid3 = gov.submit_proposal(prop3)
    print(f"   Proposal: {pid3}")
    print(f"   Status: {gov.get_proposal(pid3).approval_status.value}")

    # Case 4: Circuit breaker scenario
    print("\n[4] Circuit breaker — safety score drop")
    prop4 = ImprovementProposal(
        proposal_id="", agent_id="agent_1",
        improvement_type=ImprovementType.ARCHITECTURE_CHANGE,
        description="Replace safety module with lightweight version",
        current_state="full_safety", proposed_state="minimal_safety",
        affected_modules=["safety.py"],
        estimated_capability_change=0.3, estimated_risk_change=-0.4,
        rollback_plan="Restore full safety module",
        test_coverage=0.5, human_oversight_required=False,
    )
    # Force approve for demo
    pid4 = gov.submit_proposal(prop4)
    gov.approve_proposal(pid4, "human_admin")
    before4 = SelfImprovementSnapshot(
        snapshot_id="snap4", agent_id="agent_1", timestamp=time.time(),
        code_hash="safety_v1", capability_scores={"compute": 0.7},
        goal_alignment_score=0.8, safety_score=0.75,
    )
    result4 = gov.execute_improvement(pid4, before4)
    print(f"   Success: {result4.success}")
    print(f"   Rollback: {result4.rollback_triggered} — {result4.rollback_reason}")
    print(f"   Circuit breaker: {gov._circuit_breaker_active}")
    print(f"   Notes: {result4.notes}")

    print(f"\n[5] Stats: {gov.stats()}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
