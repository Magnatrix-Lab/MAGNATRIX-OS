#!/usr/bin/env python3
"""
MAGNATRIX-OS — Consensus Memory Engine
ai/llm_consensus_memory_native.py

Inspired by Auto-Company (github.com/MaxMiksa/Auto-Company)
Pattern: Consensus Memory — cross-cycle state relay baton.

Features:
- Consensus document management (read, write, validate format)
- Cross-cycle state relay (baton pattern)
- Section tracking: phase, actions, decisions, projects, next action, state
- Mandatory update enforcement (every cycle must update)
- Consensus history and rollback
- Diff comparison between cycles

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import deque
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("consensus_memory")


class Phase(enum.Enum):
    DAY_ZERO = "day_zero"
    EXPLORING = "exploring"
    BUILDING = "building"
    LAUNCHING = "launching"
    GROWING = "growing"
    PAUSED = "paused"


class DecisionStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    VETOED = "vetoed"
    IMPLEMENTED = "implemented"


@dataclass
class Decision:
    id: str
    description: str
    rationale: str
    status: DecisionStatus
    timestamp: float


@dataclass
class Project:
    name: str
    status: str
    next_step: str
    progress: float = 0.0


@dataclass
class CompanyState:
    product: str = "TBD"
    tech_stack: str = "TBD"
    revenue: float = 0.0
    users: int = 0


@dataclass
class Consensus:
    last_updated: str
    phase: Phase
    what_we_did: List[str] = field(default_factory=list)
    key_decisions: List[Decision] = field(default_factory=list)
    active_projects: List[Project] = field(default_factory=list)
    next_action: str = ""
    company_state: CompanyState = field(default_factory=CompanyState)
    open_questions: List[str] = field(default_factory=list)


class ConsensusMemoryEngine:
    """Consensus memory engine with baton relay pattern."""

    REQUIRED_SECTIONS = [
        "Last Updated", "Current Phase", "What We Did This Cycle",
        "Key Decisions Made", "Active Projects", "Next Action",
        "Company State", "Open Questions",
    ]

    def __init__(self, max_history: int = 100):
        self._consensus: Optional[Consensus] = None
        self._history: deque = deque(maxlen=max_history)
        self._snapshots: Dict[str, str] = {}

    def create(self, phase: Phase = Phase.DAY_ZERO) -> Consensus:
        """Create fresh consensus document."""
        consensus = Consensus(
            last_updated=self._timestamp(),
            phase=phase,
            what_we_did=[],
            key_decisions=[],
            active_projects=[],
            next_action="CEO convenes strategic meeting",
            company_state=CompanyState(),
            open_questions=[],
        )
        self._consensus = consensus
        self._save_snapshot(consensus)
        return consensus

    def update(self, **kwargs) -> Consensus:
        """Update consensus with new cycle information."""
        if self._consensus is None:
            self.create()
        consensus = self._consensus
        consensus.last_updated = self._timestamp()

        if "phase" in kwargs:
            consensus.phase = kwargs["phase"]
        if "what_we_did" in kwargs:
            consensus.what_we_did.extend(kwargs["what_we_did"])
        if "key_decisions" in kwargs:
            consensus.key_decisions.extend(kwargs["key_decisions"])
        if "active_projects" in kwargs:
            consensus.active_projects = kwargs["active_projects"]
        if "next_action" in kwargs:
            consensus.next_action = kwargs["next_action"]
        if "company_state" in kwargs:
            consensus.company_state = kwargs["company_state"]
        if "open_questions" in kwargs:
            consensus.open_questions.extend(kwargs["open_questions"])

        self._save_snapshot(consensus)
        logger.info(f"Consensus updated: phase={consensus.phase.value}, next_action={consensus.next_action}")
        return consensus

    def validate(self, consensus: Consensus) -> Tuple[bool, List[str]]:
        """Validate consensus has all required sections."""
        issues = []
        if not consensus.last_updated:
            issues.append("Missing: Last Updated")
        if not consensus.phase:
            issues.append("Missing: Current Phase")
        if not consensus.next_action:
            issues.append("Missing: Next Action")
        if consensus.phase != Phase.DAY_ZERO and not consensus.what_we_did:
            issues.append("Missing: What We Did This Cycle (mandatory for non-Day-0)")
        return len(issues) == 0, issues

    def get_current(self) -> Optional[Consensus]:
        return self._consensus

    def rollback(self, steps: int = 1) -> Optional[Consensus]:
        """Rollback to previous consensus state."""
        if len(self._history) < steps:
            return None
        for _ in range(steps):
            self._history.pop()
        if self._history:
            self._consensus = self._history[-1]
            return self._consensus
        return None

    def get_history(self, n: int = 10) -> List[Consensus]:
        return list(self._history)[-n:]

    def diff(self, cycle_a: int = -2, cycle_b: int = -1) -> Dict[str, Any]:
        """Compare two consensus cycles."""
        hist = list(self._history)
        if abs(cycle_a) > len(hist) or abs(cycle_b) > len(hist):
            return {"error": "Not enough history"}
        a = hist[cycle_a]
        b = hist[cycle_b]
        return {
            "phase_changed": a.phase != b.phase,
            "phase": (a.phase.value, b.phase.value) if a.phase != b.phase else None,
            "actions_added": len(b.what_we_did) - len(a.what_we_did),
            "decisions_added": len(b.key_decisions) - len(a.key_decisions),
            "next_action_changed": a.next_action != b.next_action,
            "next_action": (a.next_action, b.next_action) if a.next_action != b.next_action else None,
        }

    def _timestamp(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def _save_snapshot(self, consensus: Consensus) -> None:
        self._history.append(consensus)
        self._snapshots[consensus.last_updated] = self._serialize(consensus)

    def _serialize(self, consensus: Consensus) -> str:
        lines = [
            "# Consensus Memory",
            f"## Last Updated\n{consensus.last_updated}",
            f"## Current Phase\n{consensus.phase.value}",
            "## What We Did This Cycle",
        ]
        for item in consensus.what_we_did:
            lines.append(f"- {item}")
        lines.append("## Key Decisions Made")
        for d in consensus.key_decisions:
            lines.append(f"- [{d.status.value}] {d.description} | {d.rationale}")
        lines.append("## Active Projects")
        for p in consensus.active_projects:
            lines.append(f"- {p.name}: {p.status} — {p.next_step} ({p.progress:.0%})")
        lines.append(f"## Next Action\n{consensus.next_action}")
        lines.append("## Company State")
        lines.append(f"- Product: {consensus.company_state.product}")
        lines.append(f"- Tech Stack: {consensus.company_state.tech_stack}")
        lines.append(f"- Revenue: ${consensus.company_state.revenue}")
        lines.append(f"- Users: {consensus.company_state.users}")
        lines.append("## Open Questions")
        for q in consensus.open_questions:
            lines.append(f"- {q}")
        return "\n\n".join(lines)

    def export_markdown(self) -> str:
        if self._consensus is None:
            return "# Consensus Memory\n\nNo consensus established."
        return self._serialize(self._consensus)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cycles_completed": len(self._history),
            "current_phase": self._consensus.phase.value if self._consensus else None,
            "total_decisions": sum(len(c.key_decisions) for c in self._history),
            "total_projects": len(self._consensus.active_projects) if self._consensus else 0,
            "has_next_action": bool(self._consensus and self._consensus.next_action),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Consensus Memory Engine")
    print("ai/llm_consensus_memory_native.py")
    print("Pattern: Auto-Company Consensus Memory (Cross-Cycle Baton)")
    print("=" * 60)

    engine = ConsensusMemoryEngine()

    # 1. Create initial consensus
    print("[1] Create Initial Consensus (Day 0)")
    c = engine.create(Phase.DAY_ZERO)
    print(f"  Phase: {c.phase.value}")
    print(f"  Next Action: {c.next_action}")
    valid, issues = engine.validate(c)
    print(f"  Valid: {valid} ({len(issues)} issues)")

    # 2. Update after cycle 1 (brainstorm)
    print("[2] Update After Cycle 1 (Brainstorm)")
    c = engine.update(
        phase=Phase.EXPLORING,
        what_we_did=["Brainstormed 5 product ideas", "Ranked top 3 by market size"],
        key_decisions=[Decision("D1", "Focus on SaaS tools", "Higher margins, recurring revenue", DecisionStatus.APPROVED, time.time())],
        next_action="Pre-mortem and market validation for top idea",
        open_questions=["Is the market saturated?"],
    )
    print(f"  Phase: {c.phase.value}")
    print(f"  Decisions: {len(c.key_decisions)}")
    print(f"  Next Action: {c.next_action}")

    # 3. Update after cycle 2 (validation)
    print("[3] Update After Cycle 2 (Validation)")
    c = engine.update(
        phase=Phase.BUILDING,
        what_we_did=["Market validation passed", "CFO approved unit economics", "Pre-mortem: no fatal flaws found"],
        key_decisions=[Decision("D2", "GO on product Alpha", "All gates passed", DecisionStatus.APPROVED, time.time())],
        active_projects=[Project("Alpha", "building", "Setup repo and scaffold", 0.1)],
        next_action="Build MVP — core features only",
    )

    # 4. Export markdown
    print("[4] Export Markdown")
    md = engine.export_markdown()
    print(f"  {md[:300]}...")

    # 5. Diff cycles
    print("[5] Diff Between Cycles")
    diff = engine.diff(cycle_a=-2, cycle_b=-1)
    print(f"  Phase changed: {diff['phase_changed']}")
    if diff['phase_changed']:
        print(f"    {diff['phase'][0]} → {diff['phase'][1]}")
    print(f"  Next action changed: {diff['next_action_changed']}")
    print(f"  Decisions added: {diff['decisions_added']}")

    # 6. Rollback
    print("[6] Rollback Test")
    prev = engine.rollback(steps=1)
    print(f"  Rolled back. Phase: {prev.phase.value if prev else 'None'}")
    engine.update(next_action="Restored from rollback")

    # 7. Stats
    print("[7] Engine Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
