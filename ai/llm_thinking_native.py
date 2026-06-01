"""Deep Thinking / Chain of Thought Enhancer — Multi-step reasoning, verification, backtracking.

Modul ini menyediakan:
- ThoughtStep untuk single reasoning step
- ReasoningChain untuk multi-step reasoning dengan verification
- Backtracker untuk backtracking when steps fail
- VerificationEngine untuk fact-checking each step
- ThinkingOrchestrator untuk menggabungkan semua komponen
"""

from __future__ import annotations

import json
import statistics
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


class ReasoningType(Enum):
    DEDUCTIVE = auto()
    INDUCTIVE = auto()
    ABDUCTIVE = auto()
    ANALOGICAL = auto()
    CAUSAL = auto()
    COUNTERFACTUAL = auto()


@dataclass
class ThoughtStep:
    """Single step dalam reasoning chain."""
    step_id: str
    premise: str
    reasoning: str
    conclusion: str
    reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE
    status: StepStatus = StepStatus.PENDING
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    counter_arguments: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "premise": self.premise[:100],
            "reasoning": self.reasoning[:100],
            "conclusion": self.conclusion[:100],
            "type": self.reasoning_type.name,
            "status": self.status.name,
            "confidence": self.confidence
        }


@dataclass
class ReasoningChain:
    """Chain of thought dengan multiple steps."""
    chain_id: str
    question: str
    steps: List[ThoughtStep] = field(default_factory=list)
    final_answer: str = ""
    overall_confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    def add_step(self, step: ThoughtStep) -> ReasoningChain:
        self.steps.append(step)
        self._update_confidence()
        return self

    def _update_confidence(self) -> None:
        if self.steps:
            self.overall_confidence = statistics.mean([s.confidence for s in self.steps]) * (sum(1 for s in self.steps if s.status == StepStatus.VALID) / len(self.steps))

    def get_valid_steps(self) -> List[ThoughtStep]:
        return [s for s in self.steps if s.status == StepStatus.VALID]

    def get_invalid_steps(self) -> List[ThoughtStep]:
        return [s for s in self.steps if s.status == StepStatus.INVALID]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "question": self.question,
            "steps": len(self.steps),
            "valid_steps": len(self.get_valid_steps()),
            "overall_confidence": round(self.overall_confidence, 3),
            "final_answer": self.final_answer[:200]
        }


class VerificationEngine:
    """Verify individual thought steps."""

    def __init__(self):
        self._checks: List[Tuple[str, Callable[[ThoughtStep], Tuple[bool, float]]]] = []

    def add_check(self, name: str, check_fn: Callable[[ThoughtStep], Tuple[bool, float]]) -> None:
        self._checks.append((name, check_fn))

    def verify(self, step: ThoughtStep) -> ThoughtStep:
        scores = []
        for name, check in self._checks:
            valid, score = check(step)
            scores.append(score)
        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score > 0.7:
                step.status = StepStatus.VALID
            elif avg_score < 0.3:
                step.status = StepStatus.INVALID
            else:
                step.status = StepStatus.UNCERTAIN
            step.confidence = avg_score
        return step

    @staticmethod
    def default_checks() -> VerificationEngine:
        engine = VerificationEngine()
        # Check 1: Non-empty reasoning
        engine.add_check("non_empty", lambda s: (bool(s.reasoning and s.conclusion), 1.0 if (s.reasoning and s.conclusion) else 0.0))
        # Check 2: Reasoning length
        engine.add_check("length", lambda s: (len(s.reasoning) > 20, min(len(s.reasoning) / 100, 1.0)))
        # Check 3: Has evidence
        engine.add_check("evidence", lambda s: (len(s.evidence) > 0, 0.8 if s.evidence else 0.5))
        return engine


class Backtracker:
    """Backtrack ketika step invalid."""

    def __init__(self):
        self._history: List[ReasoningChain] = []

    def backtrack(self, chain: ReasoningChain, step_id: str) -> Optional[ReasoningChain]:
        """Remove invalid step dan re-build chain."""
        step_idx = None
        for i, s in enumerate(chain.steps):
            if s.step_id == step_id:
                step_idx = i
                break
        if step_idx is None:
            return None
        # Remove step and all dependent steps
        new_steps = []
        for i, s in enumerate(chain.steps):
            if i < step_idx and step_id not in s.depends_on:
                new_steps.append(s)
        chain.steps = new_steps
        chain._update_confidence()
        self._history.append(chain)
        return chain

    def get_history(self) -> List[ReasoningChain]:
        return self._history


class ThinkingOrchestrator:
    """Orchestrate deep thinking process."""

    def __init__(self, verifier: Optional[VerificationEngine] = None, backtracker: Optional[Backtracker] = None):
        self.verifier = verifier or VerificationEngine.default_checks()
        self.backtracker = backtracker or Backtracker()
        self._chains: Dict[str, ReasoningChain] = {}
        self._step_templates: Dict[str, Callable[[str, str], ThoughtStep]] = {}

    def create_chain(self, question: str) -> ReasoningChain:
        chain = ReasoningChain(str(uuid.uuid4())[:12], question)
        self._chains[chain.chain_id] = chain
        return chain

    def add_step(self, chain_id: str, premise: str, reasoning: str, conclusion: str, step_type: ReasoningType = ReasoningType.DEDUCTIVE) -> Optional[ThoughtStep]:
        chain = self._chains.get(chain_id)
        if not chain:
            return None
        step = ThoughtStep(
            step_id=str(uuid.uuid4())[:8],
            premise=premise,
            reasoning=reasoning,
            conclusion=conclusion,
            reasoning_type=step_type
        )
        chain.add_step(step)
        # Auto-verify
        self.verifier.verify(step)
        return step

    def verify_step(self, chain_id: str, step_id: str) -> Optional[ThoughtStep]:
        chain = self._chains.get(chain_id)
        if not chain:
            return None
        for step in chain.steps:
            if step.step_id == step_id:
                self.verifier.verify(step)
                return step
        return None

    def backtrack(self, chain_id: str, step_id: str) -> Optional[ReasoningChain]:
        chain = self._chains.get(chain_id)
        if not chain:
            return None
        return self.backtracker.backtrack(chain, step_id)

    def finalize(self, chain_id: str, final_answer: str) -> Optional[ReasoningChain]:
        chain = self._chains.get(chain_id)
        if not chain:
            return None
        chain.final_answer = final_answer
        chain.completed_at = time.time()
        chain._update_confidence()
        return chain

    def get_chain(self, chain_id: str) -> Optional[ReasoningChain]:
        return self._chains.get(chain_id)

    def get_best_chain(self, question: str) -> Optional[ReasoningChain]:
        chains = [c for c in self._chains.values() if c.question == question]
        if not chains:
            return None
        return max(chains, key=lambda c: c.overall_confidence)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._chains)
        completed = sum(1 for c in self._chains.values() if c.completed_at > 0)
        return {
            "total_chains": total,
            "completed": completed,
            "avg_confidence": round(statistics.mean([c.overall_confidence for c in self._chains.values()]) if self._chains else 0, 3),
            "avg_steps": round(statistics.mean([len(c.steps) for c in self._chains.values()]) if self._chains else 0, 1),
        }

    def export(self, chain_id: str, path: str) -> None:
        chain = self._chains.get(chain_id)
        if not chain:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "chain": chain.to_dict(),
                "steps": [s.to_dict() for s in chain.steps]
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("DEEP THINKING / CHAIN OF THOUGHT ENHANCER DEMO")
    print("=" * 70)

    # 1. Simple reasoning chain
    print("\n[1] Simple Reasoning Chain")
    think = ThinkingOrchestrator()
    chain = think.create_chain("Why is the sky blue?")
    think.add_step(chain.chain_id, "Light from the sun enters Earth's atmosphere", "Shorter wavelengths scatter more", "Blue light scatters more than red", ReasoningType.DEDUCTIVE)
    think.add_step(chain.chain_id, "Blue light scatters more", "Our eyes see scattered blue light from all directions", "The sky appears blue", ReasoningType.DEDUCTIVE)
    think.finalize(chain.chain_id, "The sky is blue because Rayleigh scattering preferentially scatters shorter (blue) wavelengths of sunlight.")
    print(f"  Chain: {chain.to_dict()}")
    for step in chain.steps:
        print(f"    [{step.status.name}] {step.conclusion[:60]}... (conf: {step.confidence:.2f})")

    # 2. Multi-type reasoning
    print("\n[2] Multi-Type Reasoning")
    chain2 = think.create_chain("Will it rain tomorrow?")
    think.add_step(chain2.chain_id, "Dark clouds are forming", "Dark clouds usually indicate rain", "It might rain", ReasoningType.INDUCTIVE)
    think.add_step(chain2.chain_id, "Low pressure system is moving in", "Low pressure causes moisture to rise", "Precipitation likely", ReasoningType.CAUSAL)
    think.add_step(chain2.chain_id, "Yesterday was sunny with similar clouds", "Similar conditions in past led to rain", "Pattern suggests rain", ReasoningType.ANALOGICAL)
    print(f"  Chain with {len(chain2.steps)} steps, confidence: {chain2.overall_confidence:.2f}")

    # 3. Verification
    print("\n[3] Verification")
    vchain = think.create_chain("What is 2+2?")
    step = think.add_step(vchain.chain_id, "We know that 1+1=2", "Adding 2 to 2 gives 4", "2+2=4", ReasoningType.DEDUCTIVE)
    print(f"  Before verify: {step.status.name}")
    think.verify_step(vchain.chain_id, step.step_id)
    print(f"  After verify: {step.status.name} (conf: {step.confidence:.2f})")

    # 4. Backtracking
    print("\n[4] Backtracking")
    bt_chain = think.create_chain("Solve x in 2x+4=10")
    think.add_step(bt_chain.chain_id, "2x+4=10", "Subtract 4 from both sides", "2x=6", ReasoningType.DEDUCTIVE)
    bad_step = think.add_step(bt_chain.chain_id, "2x=6", "Divide by 2", "x=4", ReasoningType.DEDUCTIVE)
    bad_step.status = StepStatus.INVALID
    bad_step.confidence = 0.0
    print(f"  Before backtrack: {len(bt_chain.steps)} steps")
    think.backtrack(bt_chain.chain_id, bad_step.step_id)
    print(f"  After backtrack: {len(bt_chain.steps)} steps")

    # 5. Counterfactual
    print("\n[5] Counterfactual Reasoning")
    cf_chain = think.create_chain("What if gravity was weaker?")
    think.add_step(cf_chain.chain_id, "Current gravity holds atmosphere", "Weaker gravity -> less atmospheric retention", "Thinner atmosphere", ReasoningType.COUNTERFACTUAL)
    think.add_step(cf_chain.chain_id, "Thinner atmosphere", "Less oxygen, more radiation", "Life would be different", ReasoningType.COUNTERFACTUAL)
    print(f"  Counterfactual chain: {len(cf_chain.steps)} steps")

    # 6. Best chain selection
    print("\n[6] Best Chain Selection")
    # Create multiple chains for same question
    for i in range(3):
        c = think.create_chain("Best chain test")
        for j in range(i + 1):
            think.add_step(c.chain_id, f"Premise {j}", f"Reasoning {j}", f"Conclusion {j}")
    best = think.get_best_chain("Best chain test")
    print(f"  Best chain has {len(best.steps) if best else 0} steps, confidence: {best.overall_confidence if best else 0:.2f}")

    # 7. Stats and export
    print("\n[7] Stats & Export")
    print(f"  Stats: {think.get_stats()}")
    think.export(chain.chain_id, "/tmp/reasoning_chain.json")
    print(f"  Exported chain to /tmp/reasoning_chain.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
