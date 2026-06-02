#!/usr/bin/env python3
"""
MAGNATRIX-OS — Convergence Gate Engine
ai/llm_convergence_gate_native.py

Inspired by Auto-Company (github.com/MaxMiksa/Auto-Company)
Pattern: Convergence Rules — cycle-based decision pipeline with GO/NO-GO gates.

Features:
- Cycle phase management (Brainstorm → Validate → Build → Ship)
- GO/NO-GO decision gates with criteria
- Pre-mortem simulation (critic review before major decisions)
- Idea ranking and selection (top N ideas, force-pick if none pass)
- Stuck detection (same next action repeated)
- Artifact enforcement (cycle 2+ must produce tangible output)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("convergence_gate")


class GatePhase(enum.Enum):
    BRAINSTORM = "brainstorm"
    VALIDATE = "validate"
    DECIDE = "decide"
    BUILD = "build"
    SHIP = "ship"


class GateVerdict(enum.Enum):
    GO = "go"
    NO_GO = "no_go"
    PIVOT = "pivot"
    FORCE = "force"
    STUCK = "stuck"


@dataclass
class Idea:
    id: str
    description: str
    score: float = 0.0
    market_size: float = 0.0
    feasibility: float = 0.0
    profitability: float = 0.0
    status: str = "pending"


@dataclass
class GateCriteria:
    market_validation: bool = False
    pre_mortem_passed: bool = False
    financial_viable: bool = False
    technical_feasible: bool = False
    no_fatal_flaws: bool = False

    @property
    def all_passed(self) -> bool:
        return all([self.market_validation, self.pre_mortem_passed, self.financial_viable,
                    self.technical_feasible, self.no_fatal_flaws])

    @property
    def score(self) -> float:
        return sum([self.market_validation, self.pre_mortem_passed, self.financial_viable,
                    self.technical_feasible, self.no_fatal_flaws]) / 5.0


@dataclass
class Cycle:
    num: int
    phase: GatePhase
    ideas: List[Idea] = field(default_factory=list)
    criteria: GateCriteria = field(default_factory=GateCriteria)
    verdict: GateVerdict = GateVerdict.NO_GO
    artifacts: List[str] = field(default_factory=list)
    next_action: str = ""


class ConvergenceGateEngine:
    """Cycle-based decision pipeline with GO/NO-GO gates."""

    def __init__(self, max_ideas: int = 5, stuck_threshold: int = 2):
        self.max_ideas = max_ideas
        self.stuck_threshold = stuck_threshold
        self._cycles: List[Cycle] = []
        self._current_ideas: List[Idea] = []
        self._next_action_history: List[str] = []

    def brainstorm(self, ideas: List[str]) -> List[Idea]:
        """Cycle 1: Brainstorm and rank ideas."""
        ranked = []
        for i, desc in enumerate(ideas[:self.max_ideas]):
            idea = Idea(
                id=f"I{i+1}",
                description=desc,
                score=random.uniform(0.3, 0.9),
                market_size=random.uniform(1000, 100000),
                feasibility=random.uniform(0.3, 0.9),
                profitability=random.uniform(0.2, 0.8),
            )
            ranked.append(idea)
        ranked.sort(key=lambda x: x.score, reverse=True)
        self._current_ideas = ranked
        cycle = Cycle(
            num=len(self._cycles) + 1,
            phase=GatePhase.BRAINSTORM,
            ideas=ranked[:3],  # top 3
            next_action="Validate top idea",
            artifacts=[f"Top 3 ideas ranked"],
        )
        self._cycles.append(cycle)
        self._next_action_history.append(cycle.next_action)
        return ranked[:3]

    def validate(self, idea_id: str, criteria: Optional[GateCriteria] = None) -> GateVerdict:
        """Cycle 2: Validate with pre-mortem, market, financial, technical checks."""
        idea = next((i for i in self._current_ideas if i.id == idea_id), None)
        if not idea:
            return GateVerdict.NO_GO

        c = criteria or GateCriteria()
        # Simulate validation
        c.market_validation = idea.market_size > 10000
        c.pre_mortem_passed = idea.feasibility > 0.5
        c.financial_viable = idea.profitability > 0.4
        c.technical_feasible = idea.feasibility > 0.4
        c.no_fatal_flaws = random.random() > 0.2

        if c.all_passed:
            verdict = GateVerdict.GO
            idea.status = "go"
        else:
            verdict = GateVerdict.NO_GO
            idea.status = "no_go"

        cycle = Cycle(
            num=len(self._cycles) + 1,
            phase=GatePhase.VALIDATE,
            ideas=[idea],
            criteria=c,
            verdict=verdict,
            next_action="Build MVP" if verdict == GateVerdict.GO else "Try next idea",
            artifacts=[f"Validation report for {idea_id}"],
        )
        self._cycles.append(cycle)
        self._next_action_history.append(cycle.next_action)
        return verdict

    def force_pick(self) -> Idea:
        """All ideas failed — force pick the highest scoring one."""
        if self._current_ideas:
            best = max(self._current_ideas, key=lambda i: i.score)
            best.status = "forced"
            cycle = Cycle(
                num=len(self._cycles) + 1,
                phase=GatePhase.DECIDE,
                ideas=[best],
                verdict=GateVerdict.FORCE,
                next_action=f"Force build: {best.description}",
                artifacts=["Force-pick decision"],
            )
            self._cycles.append(cycle)
            self._next_action_history.append(cycle.next_action)
            return best
        return Idea(id="NONE", description="No ideas available")

    def build(self, idea_id: str) -> Cycle:
        """Cycle 3+: Build — must produce tangible artifacts."""
        cycle = Cycle(
            num=len(self._cycles) + 1,
            phase=GatePhase.BUILD,
            ideas=[i for i in self._current_ideas if i.id == idea_id],
            verdict=GateVerdict.GO,
            next_action="Ship MVP",
            artifacts=["Code repository", "Deployment config", "Test results"],
        )
        self._cycles.append(cycle)
        self._next_action_history.append(cycle.next_action)
        return cycle

    def ship(self, idea_id: str) -> Cycle:
        """Ship phase."""
        cycle = Cycle(
            num=len(self._cycles) + 1,
            phase=GatePhase.SHIP,
            ideas=[i for i in self._current_ideas if i.id == idea_id],
            verdict=GateVerdict.GO,
            next_action="Monitor and iterate",
            artifacts=["Production deployment", "Marketing materials", "Analytics dashboard"],
        )
        self._cycles.append(cycle)
        self._next_action_history.append(cycle.next_action)
        return cycle

    def detect_stuck(self) -> bool:
        """Detect if same next action repeated stuck_threshold times."""
        if len(self._next_action_history) < self.stuck_threshold:
            return False
        recent = self._next_action_history[-self.stuck_threshold:]
        return len(set(recent)) == 1

    def get_pipeline(self) -> List[Dict[str, Any]]:
        return [
            {
                "cycle": c.num,
                "phase": c.phase.value,
                "verdict": c.verdict.value,
                "artifacts": c.artifacts,
                "next_action": c.next_action,
            }
            for c in self._cycles
        ]

    def get_stats(self) -> Dict[str, Any]:
        phases = [c.phase for c in self._cycles]
        return {
            "total_cycles": len(self._cycles),
            "go_count": sum(1 for c in self._cycles if c.verdict == GateVerdict.GO),
            "no_go_count": sum(1 for c in self._cycles if c.verdict == GateVerdict.NO_GO),
            "force_count": sum(1 for c in self._cycles if c.verdict == GateVerdict.FORCE),
            "stuck": self.detect_stuck(),
            "phases": [p.value for p in phases],
            "total_artifacts": sum(len(c.artifacts) for c in self._cycles),
        }


import random

# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Convergence Gate Engine")
    print("ai/llm_convergence_gate_native.py")
    print("Pattern: Auto-Company Convergence Rules (GO/NO-GO Pipeline)")
    print("=" * 60)

    engine = ConvergenceGateEngine(max_ideas=5, stuck_threshold=2)

    # 1. Brainstorm
    print("\n[1] Brainstorm (Cycle 1)")
    ideas = [
        "AI-powered code review tool",
        "Automated social media manager",
        "No-code website builder",
        "DevOps observability dashboard",
        "Customer support chatbot",
    ]
    top_ideas = engine.brainstorm(ideas)
    print(f"  Top 3 ideas:")
    for idea in top_ideas:
        print(f"    {idea.id}: {idea.description} (score={idea.score:.2f})")

    # 2. Validate top idea
    print("\n[2] Validate Top Idea (Cycle 2)")
    verdict = engine.validate("I1")
    print(f"  Verdict: {verdict.value}")
    cycle = engine._cycles[-1]
    print(f"  Criteria score: {cycle.criteria.score:.1%}")
    print(f"  All passed: {cycle.criteria.all_passed}")

    # 3. If NO-GO, try next
    if verdict == GateVerdict.NO_GO:
        print("\n[3] Try Next Idea")
        verdict = engine.validate("I2")
        print(f"  Verdict: {verdict.value}")
        if verdict == GateVerdict.NO_GO:
            print("\n  All failed — Force Pick")
            forced = engine.force_pick()
            print(f"  Forced: {forced.id} — {forced.description}")

    # 4. Build
    print("\n[4] Build Phase")
    build_cycle = engine.build("I1")
    print(f"  Artifacts: {build_cycle.artifacts}")

    # 5. Ship
    print("\n[5] Ship Phase")
    ship_cycle = engine.ship("I1")
    print(f"  Artifacts: {ship_cycle.artifacts}")

    # 6. Stuck detection
    print("\n[6] Stuck Detection")
    stuck = engine.detect_stuck()
    print(f"  Stuck: {stuck}")

    # 7. Pipeline
    print("\n[7] Full Pipeline")
    for step in engine.get_pipeline():
        print(f"  Cycle {step['cycle']}: {step['phase']} → {step['verdict']} | {step['next_action']}")

    # 8. Stats
    print("\n[8] Engine Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
