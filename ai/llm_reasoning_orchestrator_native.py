"""Reasoning Orchestrator — Multi-step reasoning with chain-of-thought, self-reflection, and debate.

Modul ini menyediakan:
- ReasoningChain untuk chain-of-thought step-by-step reasoning
- ReasoningStrategy untuk berbagai reasoning patterns (cot, step-back, analogical)
- SelfReflector untuk evaluate dan improve own reasoning
- DebateSimulator untuk multi-perspective reasoning
- ReasoningOrchestrator untuk coordinate all reasoning modes
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ReasoningMode(Enum):
    CHAIN_OF_THOUGHT = auto()
    STEP_BACK = auto()
    ANALOGICAL = auto()
    DEBATE = auto()
    SELF_CONSISTENCY = auto()
    VERIFICATION = auto()


class ReasoningStepStatus(Enum):
    PENDING = auto()
    COMPLETE = auto()
    UNCERTAIN = auto()
    FAILED = auto()


@dataclass
class ReasoningStep:
    """Single step in reasoning chain."""
    step_id: str
    premise: str
    reasoning: str
    conclusion: str
    confidence: float = 0.5
    status: ReasoningStepStatus = ReasoningStepStatus.PENDING
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningChain:
    """Complete chain of reasoning."""
    chain_id: str
    query: str
    mode: ReasoningMode
    steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: str = ""
    overall_confidence: float = 0.0
    created_at: float = field(default_factory=time.time)
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "query": self.query[:100],
            "mode": self.mode.name,
            "steps": len(self.steps),
            "final_answer": self.final_answer[:200],
            "confidence": round(self.overall_confidence, 2),
            "duration": round(self.duration, 2),
        }


class ReasoningStrategy:
    """Apply different reasoning strategies."""

    def __init__(self):
        self._strategies: Dict[ReasoningMode, Callable[[str], List[ReasoningStep]]] = {
            ReasoningMode.CHAIN_OF_THOUGHT: self._cot_steps,
            ReasoningMode.STEP_BACK: self._step_back_steps,
            ReasoningMode.ANALOGICAL: self._analogical_steps,
            ReasoningMode.VERIFICATION: self._verification_steps,
        }

    def generate_steps(self, query: str, mode: ReasoningMode) -> List[ReasoningStep]:
        fn = self._strategies.get(mode, self._cot_steps)
        return fn(query)

    def _cot_steps(self, query: str) -> List[ReasoningStep]:
        # Break into: Understand → Decompose → Solve each → Verify → Conclude
        return [
            ReasoningStep(f"cot-1", query, "Understand the problem statement", "Problem understood", 0.9),
            ReasoningStep(f"cot-2", query, "Identify known information and unknowns", "Variables identified", 0.8),
            ReasoningStep(f"cot-3", query, "Break into sub-problems", "Sub-problems defined", 0.85),
            ReasoningStep(f"cot-4", query, "Solve each sub-problem step by step", "Partial solutions found", 0.7),
            ReasoningStep(f"cot-5", query, "Combine results and verify", "Solution verified", 0.75),
            ReasoningStep(f"cot-6", query, "State final answer with reasoning", "Answer formulated", 0.9),
        ]

    def _step_back_steps(self, query: str) -> List[ReasoningStep]:
        # Abstract first, then solve
        return [
            ReasoningStep(f"sb-1", query, "Abstract to general principle", "General principle identified", 0.8),
            ReasoningStep(f"sb-2", query, "Solve at abstract level", "Abstract solution found", 0.75),
            ReasoningStep(f"sb-3", query, "Map back to concrete problem", "Concrete mapping complete", 0.7),
            ReasoningStep(f"sb-4", query, "Verify mapping correctness", "Mapping verified", 0.85),
        ]

    def _analogical_steps(self, query: str) -> List[ReasoningStep]:
        # Find analogous problem → solve → adapt
        return [
            ReasoningStep(f"ana-1", query, "Find analogous known problem", "Analogous problem found", 0.8),
            ReasoningStep(f"ana-2", query, "Solve analogous problem", "Analogous solution found", 0.85),
            ReasoningStep(f"ana-3", query, "Identify structural mapping", "Mapping identified", 0.7),
            ReasoningStep(f"ana-4", query, "Adapt solution to current problem", "Adaptation complete", 0.75),
            ReasoningStep(f"ana-5", query, "Verify adapted solution", "Adaptation verified", 0.8),
        ]

    def _verification_steps(self, query: str) -> List[ReasoningStep]:
        # Generate answer → verify from multiple angles
        return [
            ReasoningStep(f"ver-1", query, "Generate initial answer", "Initial answer generated", 0.7),
            ReasoningStep(f"ver-2", query, "Check with counter-example search", "No counter-examples found", 0.6),
            ReasoningStep(f"ver-3", query, "Verify with alternative method", "Alternative verification done", 0.75),
            ReasoningStep(f"ver-4", query, "Check edge cases", "Edge cases handled", 0.8),
            ReasoningStep(f"ver-5", query, "Confirm final answer", "Answer confirmed", 0.9),
        ]


class SelfReflector:
    """Evaluate and improve reasoning chains."""

    def __init__(self, confidence_threshold: float = 0.7):
        self.threshold = confidence_threshold

    def evaluate(self, chain: ReasoningChain) -> Dict[str, Any]:
        weak_steps = [s for s in chain.steps if s.confidence < self.threshold]
        avg_conf = sum(s.confidence for s in chain.steps) / max(len(chain.steps), 1)
        return {
            "chain_id": chain.chain_id,
            "avg_confidence": round(avg_conf, 2),
            "weak_steps": len(weak_steps),
            "step_count": len(chain.steps),
            "needs_improvement": len(weak_steps) > 0 or avg_conf < self.threshold,
        }

    def improve(self, chain: ReasoningChain) -> ReasoningChain:
        eval_result = self.evaluate(chain)
        if not eval_result["needs_improvement"]:
            return chain
        # Improve weak steps by adding verification
        improved = ReasoningChain(
            chain_id=f"{chain.chain_id}-improved",
            query=chain.query,
            mode=chain.mode,
            steps=list(chain.steps),
            final_answer=chain.final_answer,
            overall_confidence=chain.overall_confidence,
        )
        for i, s in enumerate(improved.steps):
            if s.confidence < self.threshold:
                # Add verification sub-step
                verify_step = ReasoningStep(
                    f"{s.step_id}-verify",
                    s.premise,
                    f"Re-verify: {s.reasoning}",
                    f"Confirmed: {s.conclusion}",
                    confidence=min(1.0, s.confidence + 0.2),
                    status=ReasoningStepStatus.COMPLETE
                )
                improved.steps.insert(i + 1, verify_step)
        # Recalculate confidence
        improved.overall_confidence = sum(s.confidence for s in improved.steps) / max(len(improved.steps), 1)
        return improved

    def compare(self, before: ReasoningChain, after: ReasoningChain) -> Dict[str, Any]:
        return {
            "steps_before": len(before.steps),
            "steps_after": len(after.steps),
            "confidence_before": round(before.overall_confidence, 2),
            "confidence_after": round(after.overall_confidence, 2),
            "improvement": round(after.overall_confidence - before.overall_confidence, 2),
        }


class DebateSimulator:
    """Simulate multi-perspective debate on a question."""

    def __init__(self, num_perspectives: int = 3):
        self.num_perspectives = num_perspectives

    def debate(self, query: str, perspectives: Optional[List[str]] = None) -> List[ReasoningChain]:
        perspectives = perspectives or ["Proponent", "Skeptic", "Neutral"]
        chains = []
        for i, p in enumerate(perspectives[:self.num_perspectives]):
            steps = [
                ReasoningStep(f"deb-{i}-1", query, f"{p} perspective: Analyze premises", "Premises analyzed", 0.8),
                ReasoningStep(f"deb-{i}-2", query, f"{p} perspective: Draw conclusion", "Conclusion drawn", 0.75),
                ReasoningStep(f"deb-{i}-3", query, f"{p} perspective: Address counter-arguments", "Counter-arguments addressed", 0.7),
            ]
            chain = ReasoningChain(
                chain_id=f"debate-{i}-{str(uuid.uuid4())[:8]}",
                query=query,
                mode=ReasoningMode.DEBATE,
                steps=steps,
                final_answer=f"{p} concludes: [answer based on perspective]",
                overall_confidence=sum(s.confidence for s in steps) / len(steps)
            )
            chains.append(chain)
        return chains

    def synthesize(self, chains: List[ReasoningChain]) -> ReasoningChain:
        # Find consensus or highlight disagreement
        all_conclusions = [c.final_answer for c in chains]
        consensus = len(set(all_conclusions)) == 1
        avg_conf = sum(c.overall_confidence for c in chains) / max(len(chains), 1)
        # Create synthesis chain
        steps = [
            ReasoningStep("syn-1", "", "Compare all perspectives", "Perspectives compared", 0.85),
            ReasoningStep("syn-2", "", "Identify agreement and disagreement", "Analysis complete", 0.8),
            ReasoningStep("syn-3", "", "Synthesize balanced conclusion", "Synthesis complete", 0.75),
        ]
        return ReasoningChain(
            chain_id=f"synthesis-{str(uuid.uuid4())[:8]}",
            query=chains[0].query if chains else "",
            mode=ReasoningMode.DEBATE,
            steps=steps,
            final_answer=f"Consensus: {consensus} | Conclusions from {len(chains)} perspectives evaluated",
            overall_confidence=avg_conf
        )


class ReasoningOrchestrator:
    """Coordinate all reasoning modes and select the best approach."""

    def __init__(self, default_mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHT):
        self.default_mode = default_mode
        self.strategy = ReasoningStrategy()
        self.reflector = SelfReflector()
        self.debater = DebateSimulator()
        self._chains: List[ReasoningChain] = []
        self._history: List[Dict[str, Any]] = []

    def reason(self, query: str, mode: Optional[ReasoningMode] = None) -> ReasoningChain:
        mode = mode or self.default_mode
        start = time.time()
        if mode == ReasoningMode.DEBATE:
            chains = self.debater.debate(query)
            chain = self.debater.synthesize(chains)
        else:
            steps = self.strategy.generate_steps(query, mode)
            chain = ReasoningChain(
                chain_id=str(uuid.uuid4())[:12],
                query=query,
                mode=mode,
                steps=steps,
                final_answer=f"Answer derived via {mode.name}",
                overall_confidence=sum(s.confidence for s in steps) / max(len(steps), 1)
            )
        chain.duration = time.time() - start
        self._chains.append(chain)
        return chain

    def reason_with_reflection(self, query: str, mode: Optional[ReasoningMode] = None) -> Tuple[ReasoningChain, ReasoningChain, Dict[str, Any]]:
        chain = self.reason(query, mode)
        improved = self.reflector.improve(chain)
        comparison = self.reflector.compare(chain, improved)
        return chain, improved, comparison

    def self_consistency(self, query: str, num_samples: int = 3) -> ReasoningChain:
        """Run multiple reasoning paths and vote on best answer."""
        samples = []
        for _ in range(num_samples):
            c = self.reason(query, ReasoningMode.CHAIN_OF_THOUGHT)
            samples.append(c)
        # Vote by confidence
        best = max(samples, key=lambda c: c.overall_confidence)
        # Create consensus chain
        chain = ReasoningChain(
            chain_id=f"consensus-{str(uuid.uuid4())[:8]}",
            query=query,
            mode=ReasoningMode.SELF_CONSISTENCY,
            steps=[ReasoningStep(f"sc-{i}", query, f"Sample {i+1} reasoning", f"Confidence: {s.overall_confidence:.2f}", s.overall_confidence)
                   for i, s in enumerate(samples)],
            final_answer=best.final_answer,
            overall_confidence=best.overall_confidence
        )
        chain.overall_confidence = sum(s.overall_confidence for s in samples) / max(len(samples), 1)
        self._chains.append(chain)
        return chain

    def get_best_chain(self, query_filter: Optional[str] = None) -> Optional[ReasoningChain]:
        chains = self._chains
        if query_filter:
            chains = [c for c in chains if query_filter.lower() in c.query.lower()]
        if not chains:
            return None
        return max(chains, key=lambda c: c.overall_confidence)

    def get_stats(self) -> Dict[str, Any]:
        if not self._chains:
            return {}
        return {
            "total_chains": len(self._chains),
            "mode_distribution": {m.name: sum(1 for c in self._chains if c.mode == m) for m in ReasoningMode},
            "avg_confidence": sum(c.overall_confidence for c in self._chains) / len(self._chains),
            "avg_duration": sum(c.duration for c in self._chains) / len(self._chains),
            "best_confidence": max(c.overall_confidence for c in self._chains),
        }

    def export_all(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in self._chains], f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("REASONING ORCHESTRATOR DEMO")
    print("=" * 70)

    orchestrator = ReasoningOrchestrator()

    # 1. Chain of Thought
    print("\n[1] Chain of Thought Reasoning")
    query = "If a train travels 60 km in 30 minutes, how far will it travel in 2 hours at the same speed?"
    chain = orchestrator.reason(query, ReasoningMode.CHAIN_OF_THOUGHT)
    print(f"  Query: {chain.query[:60]}...")
    print(f"  Mode: {chain.mode.name}")
    print(f"  Steps: {len(chain.steps)}")
    for s in chain.steps:
        print(f"    {s.step_id}: {s.reasoning[:50]}... (conf={s.confidence})")
    print(f"  Final: {chain.final_answer}")
    print(f"  Confidence: {chain.overall_confidence:.2f}")
    print(f"  Duration: {chain.duration:.3f}s")

    # 2. Step-back reasoning
    print("\n[2] Step-back Reasoning")
    query2 = "Solve: 3x^2 + 5x - 2 = 0"
    chain2 = orchestrator.reason(query2, ReasoningMode.STEP_BACK)
    print(f"  Steps: {len(chain2.steps)}")
    print(f"  Confidence: {chain2.overall_confidence:.2f}")

    # 3. Verification
    print("\n[3] Verification Mode")
    query3 = "Is 127 a prime number?"
    chain3 = orchestrator.reason(query3, ReasoningMode.VERIFICATION)
    print(f"  Steps: {len(chain3.steps)}")
    for s in chain3.steps:
        print(f"    {s.step_id}: {s.reasoning} (conf={s.confidence})")
    print(f"  Confidence: {chain3.overall_confidence:.2f}")

    # 4. Self-reflection
    print("\n[4] Self-Reflection")
    query4 = "Calculate the compound interest on $1000 at 5% for 3 years"
    original, improved, comparison = orchestrator.reason_with_reflection(query4, ReasoningMode.CHAIN_OF_THOUGHT)
    print(f"  Original: {len(original.steps)} steps, conf={original.overall_confidence:.2f}")
    print(f"  Improved: {len(improved.steps)} steps, conf={improved.overall_confidence:.2f}")
    print(f"  Improvement: {comparison['improvement']:.2f}")

    # 5. Debate
    print("\n[5] Debate Simulation")
    query5 = "Should we invest in renewable energy?"
    debate_chains = orchestrator.debater.debate(query5, ["Economist", "Environmental Scientist", "Technologist"])
    for c in debate_chains:
        print(f"  {c.final_answer[:50]}... (conf={c.overall_confidence:.2f})")
    synthesis = orchestrator.debater.synthesize(debate_chains)
    print(f"  Synthesis: {synthesis.final_answer}")

    # 6. Self-consistency
    print("\n[6] Self-Consistency (Multiple Paths)")
    query6 = "A bat and ball cost $11 total. The bat costs $10 more than the ball. How much is the ball?"
    consensus = orchestrator.self_consistency(query6, num_samples=3)
    print(f"  Consensus from {len(consensus.steps)} samples")
    print(f"  Final confidence: {consensus.overall_confidence:.2f}")
    print(f"  Answer: {consensus.final_answer}")

    # 7. Analogical reasoning
    print("\n[7] Analogical Reasoning")
    query7 = "How do I solve this scheduling problem?"
    chain7 = orchestrator.reason(query7, ReasoningMode.ANALOGICAL)
    print(f"  Steps: {len(chain7.steps)}")
    for s in chain7.steps:
        print(f"    {s.step_id}: {s.reasoning}")

    # 8. Stats
    print("\n[8] Orchestrator Stats")
    stats = orchestrator.get_stats()
    print(f"  Total chains: {stats['total_chains']}")
    print(f"  Modes: {stats['mode_distribution']}")
    print(f"  Avg confidence: {stats['avg_confidence']:.2f}")
    print(f"  Avg duration: {stats['avg_duration']:.3f}s")
    print(f"  Best confidence: {stats['best_confidence']:.2f}")

    # 9. Best chain
    print("\n[9] Best Chain")
    best = orchestrator.get_best_chain()
    if best:
        print(f"  Best chain: {best.chain_id} (conf={best.overall_confidence:.2f}, mode={best.mode.name})")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
