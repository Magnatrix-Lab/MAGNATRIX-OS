"""Chain-of-Thought Engine — Structured reasoning with explicit steps, verification, and refinement.

Modul ini menyediakan:
- ThoughtStep untuk single reasoning step
- ReasoningChain untuk chain multiple steps
- ThoughtVerifier untuk verify each step's correctness
- ChainRefiner untuk refine and improve chains
- CoTEngine untuk end-to-end CoT reasoning
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class StepStatus(Enum):
    PENDING = auto()
    VALID = auto()
    INVALID = auto()
    UNCERTAIN = auto()


@dataclass
class ThoughtStep:
    """Single step in reasoning chain."""
    step_id: str
    premise: str
    reasoning: str
    conclusion: str
    confidence: float = 1.0
    status: StepStatus = StepStatus.PENDING
    evidence: List[str] = field(default_factory=list)
    substeps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "premise": self.premise[:100],
            "reasoning": self.reasoning[:100],
            "conclusion": self.conclusion[:100],
            "confidence": self.confidence,
            "status": self.status.name,
        }


@dataclass
class ReasoningChain:
    """Complete chain of reasoning."""
    chain_id: str
    query: str
    steps: List[ThoughtStep] = field(default_factory=list)
    final_answer: str = ""
    overall_confidence: float = 0.0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    status: str = "incomplete"

    def add_step(self, step: ThoughtStep) -> None:
        self.steps.append(step)

    def compute_confidence(self) -> float:
        if not self.steps:
            return 0.0
        confidences = [s.confidence for s in self.steps if s.status == StepStatus.VALID]
        if not confidences:
            return 0.0
        # Overall confidence is product of step confidences
        prod = 1.0
        for c in confidences:
            prod *= c
        self.overall_confidence = prod ** (1.0 / len(confidences))
        return self.overall_confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "query": self.query[:100],
            "steps": len(self.steps),
            "final_answer": self.final_answer[:100],
            "confidence": round(self.overall_confidence, 3),
            "status": self.status,
        }


class ThoughtVerifier:
    """Verify correctness of reasoning steps."""

    def __init__(self):
        self._checks: List[Tuple[str, Callable[[ThoughtStep], Tuple[bool, str]]]] = []

    def add_check(self, name: str, check_fn: Callable[[ThoughtStep], Tuple[bool, str]]) -> None:
        self._checks.append((name, check_fn))

    def verify(self, step: ThoughtStep) -> StepStatus:
        issues = []
        for name, check_fn in self._checks:
            valid, message = check_fn(step)
            if not valid:
                issues.append(f"{name}: {message}")
        if issues:
            step.status = StepStatus.INVALID
            step.metadata["issues"] = issues
            return StepStatus.INVALID
        step.status = StepStatus.VALID
        return StepStatus.VALID

    @staticmethod
    def has_content(step: ThoughtStep) -> Tuple[bool, str]:
        return (len(step.reasoning) > 10, "Reasoning too short")

    @staticmethod
    def has_conclusion(step: ThoughtStep) -> Tuple[bool, str]:
        return (len(step.conclusion) > 5, "Missing conclusion")

    @staticmethod
    def reasonable_confidence(step: ThoughtStep) -> Tuple[bool, str]:
        return (0.0 <= step.confidence <= 1.0, "Confidence out of range")

    @staticmethod
    def default_checks() -> List[Tuple[str, Callable[[ThoughtStep], Tuple[bool, str]]]]:
        return [
            ("content", ThoughtVerifier.has_content),
            ("conclusion", ThoughtVerifier.has_conclusion),
            ("confidence", ThoughtVerifier.reasonable_confidence),
        ]


class ChainRefiner:
    """Refine and improve reasoning chains."""

    def refine(self, chain: ReasoningChain, refiner_fn: Optional[Callable[[ReasoningChain], ReasoningChain]] = None) -> ReasoningChain:
        refiner_fn = refiner_fn or self._default_refiner
        return refiner_fn(chain)

    def _default_refiner(self, chain: ReasoningChain) -> ReasoningChain:
        # Add verification step if missing
        if not any("verify" in s.step_id for s in chain.steps):
            verify_step = ThoughtStep(
                step_id=f"{chain.chain_id}-verify",
                premise="Verify all previous steps",
                reasoning="Checking consistency and correctness of all reasoning steps",
                conclusion="All steps verified" if all(s.status == StepStatus.VALID for s in chain.steps) else "Some steps need review",
                confidence=min(s.confidence for s in chain.steps) if chain.steps else 0.0,
            )
            chain.add_step(verify_step)
        chain.compute_confidence()
        chain.status = "complete" if chain.overall_confidence > 0.5 else "incomplete"
        return chain

    def expand_step(self, chain: ReasoningChain, step_id: str, substeps: List[ThoughtStep]) -> bool:
        for step in chain.steps:
            if step.step_id == step_id:
                step.substeps = [s.step_id for s in substeps]
                # Insert substeps after parent
                idx = chain.steps.index(step)
                for s in substeps:
                    chain.steps.insert(idx + 1, s)
                    idx += 1
                return True
        return False


class CoTEngine:
    """End-to-end Chain-of-Thought reasoning engine."""

    def __init__(self):
        self.verifier = ThoughtVerifier()
        for name, check in ThoughtVerifier.default_checks():
            self.verifier.add_check(name, check)
        self.refiner = ChainRefiner()
        self._chains: List[ReasoningChain] = []
        self._templates: Dict[str, List[str]] = {}
        self._init_templates()

    def _init_templates(self) -> None:
        self._templates = {
            "math": ["Understand the problem", "Identify known values", "Apply formula", "Calculate result", "Verify answer"],
            "logic": ["Identify premises", "Apply logical rules", "Derive conclusion", "Check for contradictions"],
            "analysis": ["Gather information", "Identify patterns", "Form hypothesis", "Test hypothesis", "Draw conclusion"],
            "planning": ["Define goal", "Identify constraints", "List options", "Evaluate options", "Select best path"],
        }

    def reason(self, query: str, domain: str = "general", step_generator: Optional[Callable[[str, str], List[ThoughtStep]]] = None) -> ReasoningChain:
        chain = ReasoningChain(
            chain_id=str(uuid.uuid4())[:12],
            query=query,
        )
        step_generator = step_generator or self._default_generator
        steps = step_generator(query, domain)
        for step in steps:
            self.verifier.verify(step)
            chain.add_step(step)
        chain = self.refiner.refine(chain)
        chain.completed_at = time.time()
        self._chains.append(chain)
        return chain

    def _default_generator(self, query: str, domain: str) -> List[ThoughtStep]:
        template = self._templates.get(domain, self._templates["analysis"])
        steps = []
        for i, desc in enumerate(template):
            step = ThoughtStep(
                step_id=f"step-{i}",
                premise=query[:100],
                reasoning=f"{desc}: analyzing the problem",
                conclusion=f"Intermediate result from {desc}",
                confidence=0.8 - i * 0.05,
            )
            steps.append(step)
        return steps

    def multi_step_reason(self, query: str, max_steps: int = 5) -> ReasoningChain:
        chain = ReasoningChain(
            chain_id=str(uuid.uuid4())[:12],
            query=query,
        )
        current = query
        for i in range(max_steps):
            step = ThoughtStep(
                step_id=f"step-{i}",
                premise=current[:100],
                reasoning=f"Step {i+1}: Reasoning about {current[:50]}",
                conclusion=f"Result after step {i+1}",
                confidence=0.9 - i * 0.1,
            )
            self.verifier.verify(step)
            chain.add_step(step)
            current = f"Based on: {step.conclusion}, next step..."
        chain.final_answer = f"Answer derived from {max_steps} steps of reasoning"
        chain = self.refiner.refine(chain)
        chain.completed_at = time.time()
        self._chains.append(chain)
        return chain

    def get_best_chain(self, query: Optional[str] = None) -> Optional[ReasoningChain]:
        chains = self._chains
        if query:
            chains = [c for c in chains if query.lower() in c.query.lower()]
        if not chains:
            return None
        return max(chains, key=lambda c: c.overall_confidence)

    def get_stats(self) -> Dict[str, Any]:
        if not self._chains:
            return {}
        return {
            "total_chains": len(self._chains),
            "avg_steps": sum(len(c.steps) for c in self._chains) / len(self._chains),
            "avg_confidence": sum(c.overall_confidence for c in self._chains) / len(self._chains),
            "complete_chains": sum(1 for c in self._chains if c.status == "complete"),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in self._chains], f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CHAIN-OF-THOUGHT ENGINE DEMO")
    print("=" * 70)

    engine = CoTEngine()

    # 1. Math reasoning
    print("\n[1] Math Reasoning")
    chain = engine.reason("If a train travels 60 km in 30 minutes, how far in 2 hours?", domain="math")
    print(f"  Query: {chain.query}")
    print(f"  Steps: {len(chain.steps)}")
    for s in chain.steps:
        print(f"    {s.step_id}: {s.reasoning[:50]}... -> {s.conclusion[:40]}... (conf={s.confidence}, status={s.status.name})")
    print(f"  Final: {chain.final_answer}")
    print(f"  Confidence: {chain.overall_confidence:.3f}")

    # 2. Logic reasoning
    print("\n[2] Logic Reasoning")
    chain2 = engine.reason("All cats are mammals. Some mammals are pets. Are all cats pets?", domain="logic")
    print(f"  Steps: {len(chain2.steps)}, Confidence: {chain2.overall_confidence:.3f}")
    for s in chain2.steps:
        print(f"    {s.step_id}: {s.reasoning[:50]}... (status={s.status.name})")

    # 3. Multi-step with custom generator
    print("\n[3] Multi-Step Custom Reasoning")
    def custom_gen(query, domain):
        return [
            ThoughtStep("s1", query, "Define the problem clearly", "Problem defined", 0.9),
            ThoughtStep("s2", query, "Break into sub-problems", "Sub-problems identified", 0.85),
            ThoughtStep("s3", query, "Solve each sub-problem", "Solutions found", 0.8),
            ThoughtStep("s4", query, "Combine results", "Combined solution", 0.75),
        ]
    chain3 = engine.reason("Design a microservices architecture", domain="planning", step_generator=custom_gen)
    print(f"  Steps: {len(chain3.steps)}, Status: {chain3.status}")

    # 4. Step expansion
    print("\n[4] Step Expansion")
    substeps = [
        ThoughtStep("s2a", "Break into sub-problems", "Identify services", "Services identified", 0.9),
        ThoughtStep("s2b", "Break into sub-problems", "Define interfaces", "Interfaces defined", 0.85),
    ]
    expanded = engine.refiner.expand_step(chain3, "s2", substeps)
    print(f"  Expanded: {expanded}, Total steps now: {len(chain3.steps)}")

    # 5. Invalid step detection
    print("\n[5] Invalid Step Detection")
    bad_step = ThoughtStep("bad", "test", "x", "y", confidence=1.5)
    result = engine.verifier.verify(bad_step)
    print(f"  Bad step status: {result.name}")
    print(f"  Issues: {bad_step.metadata.get('issues', [])}")

    # 6. Chain stats
    print(f"\n[6] Engine Stats")
    print(f"  {engine.get_stats()}")

    # 7. Best chain
    print("\n[7] Best Chain")
    best = engine.get_best_chain()
    if best:
        print(f"  Best chain: {best.chain_id}, confidence={best.overall_confidence:.3f}")

    # 8. Export
    print("\n[8] Export")
    engine.export("/tmp/cot_chains.json")
    print("  Exported to /tmp/cot_chains.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
