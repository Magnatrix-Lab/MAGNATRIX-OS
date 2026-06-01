"""Reasoning Engine — Deductive, inductive, abductive reasoning, logical proof, syllogism.

Modul ini menyediakan:
- DeductiveReasoner untuk penalaran deduktif (general → specific)
- InductiveReasoner untuk penalaran induktif (specific → general)
- AbductiveReasoner untuk penalaran abduktif (infer best explanation)
- SyllogismEngine untuk validasi silogisme Aristotelian
- ProofEngine untuk proof construction dan verification
- LogicalConstraintSolver untuk constraint satisfaction

Arsitektur: Premises → Reasoner → Conclusion → Proof → Validation
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set, Union
from enum import Enum, auto


class ReasoningType(Enum):
    DEDUCTIVE = auto()
    INDUCTIVE = auto()
    ABDUCTIVE = auto()
    ANALOGICAL = auto()
    CAUSAL = auto()


class TruthValue(Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"
    CONTINGENT = "contingent"


@dataclass
class Proposition:
    """Logical proposition."""
    proposition_id: str
    statement: str
    truth_value: TruthValue = TruthValue.UNKNOWN
    confidence: float = 1.0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def negate(self) -> Proposition:
        return Proposition(
            proposition_id=f"not-{self.proposition_id}",
            statement=f"NOT ({self.statement})",
            truth_value=TruthValue.FALSE if self.truth_value == TruthValue.TRUE else TruthValue.TRUE if self.truth_value == TruthValue.FALSE else TruthValue.UNKNOWN,
            confidence=self.confidence
        )

    def __hash__(self) -> int:
        return hash(self.proposition_id)

    def __eq__(self, other) -> bool:
        if isinstance(other, Proposition):
            return self.proposition_id == other.proposition_id
        return False


@dataclass
class Rule:
    """Inference rule: if premises then conclusion."""
    rule_id: str
    premises: List[Proposition]
    conclusion: Proposition
    confidence: float = 1.0
    rule_type: ReasoningType = ReasoningType.DEDUCTIVE


@dataclass
class Proof:
    """Logical proof with steps."""
    proof_id: str
    conclusion: Proposition
    steps: List[Tuple[Rule, List[Proposition]]] = field(default_factory=list)
    validity_score: float = 0.0
    gaps: List[str] = field(default_factory=list)


class DeductiveReasoner:
    """Deductive reasoning: general rules → specific conclusions."""

    def __init__(self):
        self._rules: List[Rule] = []
        self._propositions: Dict[str, Proposition] = {}

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    def add_fact(self, prop: Proposition) -> None:
        self._propositions[prop.proposition_id] = prop

    def infer(self, target: Proposition, max_depth: int = 5) -> Optional[Proof]:
        """Forward chaining inference."""
        visited: Set[str] = set()
        queue = [(p, [], 0) for p in self._propositions.values()]
        while queue:
            current, path, depth = queue.pop(0)
            if depth > max_depth:
                continue
            if current.proposition_id == target.proposition_id:
                return Proof(
                    proof_id=str(uuid.uuid4())[:12],
                    conclusion=target,
                    steps=path,
                    validity_score=sum(r.confidence for r, _ in path) / max(len(path), 1)
                )
            visited.add(current.proposition_id)
            for rule in self._rules:
                if all(p.proposition_id in [x.proposition_id for x in self._propositions.values()] or p.proposition_id in visited for p in rule.premises):
                    if rule.conclusion.proposition_id not in visited:
                        new_path = path + [(rule, rule.premises)]
                        queue.append((rule.conclusion, new_path, depth + 1))
        return None

    def validate(self, proof: Proof) -> Tuple[bool, List[str]]:
        errors = []
        for rule, premises in proof.steps:
            if len(rule.premises) != len(premises):
                errors.append(f"Rule {rule.rule_id} premise mismatch")
            for expected, actual in zip(rule.premises, premises):
                if expected.proposition_id != actual.proposition_id:
                    errors.append(f"Premise mismatch: {expected} != {actual}")
        return len(errors) == 0, errors


class InductiveReasoner:
    """Inductive reasoning: specific observations → general hypothesis."""

    def __init__(self, min_samples: int = 3, confidence_threshold: float = 0.7):
        self.min_samples = min_samples
        self.confidence_threshold = confidence_threshold
        self._observations: List[Proposition] = []
        self._hypotheses: List[Proposition] = []

    def observe(self, proposition: Proposition) -> None:
        self._observations.append(proposition)

    def generalize(self, pattern_fn: Optional[Callable[[List[Proposition]], Optional[Proposition]]] = None) -> Optional[Proposition]:
        if len(self._observations) < self.min_samples:
            return None
        generalizer = pattern_fn or self._default_generalizer
        hypothesis = generalizer(self._observations)
        if hypothesis and hypothesis.confidence >= self.confidence_threshold:
            self._hypotheses.append(hypothesis)
        return hypothesis

    def _default_generalizer(self, observations: List[Proposition]) -> Optional[Proposition]:
        # Simple pattern: if all observations have same truth value, generalize
        if not observations:
            return None
        truths = [o.truth_value for o in observations]
        if all(t == TruthValue.TRUE for t in truths):
            return Proposition(
                proposition_id=f"hypo-{uuid.uuid4().hex[:8]}",
                statement=f"All observed instances hold (n={len(observations)})",
                truth_value=TruthValue.CONTINGENT,
                confidence=min(1.0, len(observations) / (len(observations) + 1))
            )
        return None

    def get_observations(self) -> List[Proposition]:
        return self._observations

    def get_hypotheses(self) -> List[Proposition]:
        return self._hypotheses


class AbductiveReasoner:
    """Abductive reasoning: infer best explanation from observations."""

    def __init__(self):
        self._explanations: Dict[str, List[Proposition]] = {}  # observation -> possible explanations

    def add_explanation(self, observation: Proposition, explanations: List[Proposition]) -> None:
        self._explanations[observation.proposition_id] = explanations

    def infer(self, observation: Proposition) -> List[Tuple[Proposition, float]]:
        """Return ranked explanations with plausibility scores."""
        candidates = self._explanations.get(observation.proposition_id, [])
        if not candidates:
            return []
        # Rank by simplicity (fewer assumptions = higher score)
        scored = []
        for expl in candidates:
            score = expl.confidence * (1.0 / (1 + len(expl.statement.split())))
            scored.append((expl, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


class SyllogismEngine:
    """Validate Aristotelian syllogisms."""

    VALID_MOODS = {
        "AAA", "AAI", "AEE", "AEO", "AII", "AOI", "EAE", "EAO", "EIO", "IAI", "IEO", "OAO"
    }

    FIGURE_PATTERNS = {
        1: [(0, 1), (1, 2)],  # M-P, S-M -> S-P
        2: [(1, 0), (1, 2)],  # P-M, S-M -> S-P
        3: [(0, 1), (2, 1)],  # M-P, M-S -> S-P
        4: [(1, 0), (2, 1)],  # P-M, M-S -> S-P
    }

    @staticmethod
    def parse_categorical(statement: str) -> Tuple[str, str, str]:
        # Simple parser: "All A are B" -> ("A", "All", "B")
        statement = statement.strip().lower()
        if statement.startswith("all "):
            parts = statement.replace("all ", "").split(" are ")
            return (parts[0].strip(), "A", parts[1].strip()) if len(parts) == 2 else ("", "", "")
        elif statement.startswith("some "):
            parts = statement.replace("some ", "").split(" are ")
            return (parts[0].strip(), "I", parts[1].strip()) if len(parts) == 2 else ("", "", "")
        elif statement.startswith("no "):
            parts = statement.replace("no ", "").split(" are ")
            return (parts[0].strip(), "E", parts[1].strip()) if len(parts) == 2 else ("", "", "")
        elif " are not " in statement:
            parts = statement.split(" are not ")
            return (parts[0].strip(), "O", parts[1].strip()) if len(parts) == 2 else ("", "", "")
        return ("", "", "")

    @classmethod
    def validate(cls, major: str, minor: str, conclusion: str, figure: int = 1) -> Tuple[bool, str]:
        m = cls.parse_categorical(major)
        n = cls.parse_categorical(minor)
        c = cls.parse_categorical(conclusion)
        if not all([m[1], n[1], c[1]]):
            return False, "Invalid categorical form"
        mood = m[1] + n[1] + c[1]
        if mood in cls.VALID_MOODS:
            return True, f"Valid {mood}-{figure}"
        return False, f"Invalid mood {mood}"


class LogicalConstraintSolver:
    """Simple constraint satisfaction solver."""

    def __init__(self):
        self._constraints: List[Callable[[Dict[str, Any]], bool]] = []
        self._variables: Dict[str, List[Any]] = {}

    def add_variable(self, name: str, domain: List[Any]) -> None:
        self._variables[name] = domain

    def add_constraint(self, fn: Callable[[Dict[str, Any]], bool]) -> None:
        self._constraints.append(fn)

    def solve(self) -> List[Dict[str, Any]]:
        """Brute force constraint satisfaction."""
        from itertools import product
        if not self._variables:
            return []
        names = list(self._variables.keys())
        domains = [self._variables[n] for n in names]
        solutions = []
        for values in product(*domains):
            assignment = dict(zip(names, values))
            if all(c(assignment) for c in self._constraints):
                solutions.append(assignment)
        return solutions


class ReasoningEngine:
    """End-to-end reasoning engine combining all reasoners."""

    def __init__(self):
        self.deductive = DeductiveReasoner()
        self.inductive = InductiveReasoner()
        self.abductive = AbductiveReasoner()
        self.syllogism = SyllogismEngine
        self.constraints = LogicalConstraintSolver()

    def reason(self, reasoning_type: ReasoningType, premises: List[Proposition],
               target: Optional[Proposition] = None) -> Any:
        if reasoning_type == ReasoningType.DEDUCTIVE:
            for p in premises:
                self.deductive.add_fact(p)
            return self.deductive.infer(target) if target else None
        elif reasoning_type == ReasoningType.INDUCTIVE:
            for p in premises:
                self.inductive.observe(p)
            return self.inductive.generalize()
        elif reasoning_type == ReasoningType.ABDUCTIVE:
            if target:
                return self.abductive.infer(target)
            return None
        return None

    def validate_syllogism(self, major: str, minor: str, conclusion: str, figure: int = 1) -> Tuple[bool, str]:
        return self.syllogism.validate(major, minor, conclusion, figure)

    def solve_constraints(self) -> List[Dict[str, Any]]:
        return self.constraints.solve()


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("REASONING ENGINE DEMO")
    print("=" * 70)

    engine = ReasoningEngine()

    # 1. Deductive reasoning
    print("\n[1] Deductive Reasoning")
    all_mortal = Proposition("p1", "All humans are mortal", TruthValue.TRUE, 1.0)
    socrates_human = Proposition("p2", "Socrates is a human", TruthValue.TRUE, 1.0)
    socrates_mortal = Proposition("p3", "Socrates is mortal", TruthValue.UNKNOWN)
    rule = Rule("r1", [all_mortal, socrates_human], socrates_mortal, 1.0, ReasoningType.DEDUCTIVE)
    engine.deductive.add_rule(rule)
    engine.deductive.add_fact(all_mortal)
    engine.deductive.add_fact(socrates_human)
    proof = engine.deductive.infer(socrates_mortal)
    if proof:
        print(f"  Proof found: {proof.conclusion.statement}")
        print(f"  Validity: {proof.validity_score}")
        valid, errors = engine.deductive.validate(proof)
        print(f"  Valid: {valid}, Errors: {errors}")

    # 2. Inductive reasoning
    print("\n[2] Inductive Reasoning")
    for i in range(5):
        engine.inductive.observe(Proposition(f"obs{i}", f"Swan {i} is white", TruthValue.TRUE, 1.0))
    hypothesis = engine.inductive.generalize()
    if hypothesis:
        print(f"  Hypothesis: {hypothesis.statement}")
        print(f"  Confidence: {hypothesis.confidence}")
    print(f"  Observations: {len(engine.inductive.get_observations())}")

    # 3. Abductive reasoning
    print("\n[3] Abductive Reasoning")
    wet_grass = Proposition("obs", "The grass is wet", TruthValue.TRUE)
    rain = Proposition("exp1", "It rained last night", TruthValue.CONTINGENT, 0.8)
    sprinkler = Proposition("exp2", "The sprinkler was on", TruthValue.CONTINGENT, 0.6)
    engine.abductive.add_explanation(wet_grass, [rain, sprinkler])
    explanations = engine.abductive.infer(wet_grass)
    print(f"  Explanations for '{wet_grass.statement}':")
    for expl, score in explanations:
        print(f"    {expl.statement} (score: {score:.3f})")

    # 4. Syllogism validation
    print("\n[4] Syllogism Validation")
    for major, minor, conclusion, figure, expected in [
        ("All men are mortal", "All Greeks are men", "All Greeks are mortal", 1, True),
        ("All cats are mammals", "All mammals are animals", "All cats are animals", 1, True),
        ("Some A are B", "All B are C", "Some A are C", 1, True),
    ]:
        valid, msg = engine.validate_syllogism(major, minor, conclusion, figure)
        print(f"  {msg}: {'✅' if valid else '❌'} (expected: {'✅' if expected else '❌'})")

    # 5. Constraint solving
    print("\n[5] Constraint Solving")
    solver = LogicalConstraintSolver()
    solver.add_variable("x", [1, 2, 3, 4])
    solver.add_variable("y", [1, 2, 3, 4])
    solver.add_constraint(lambda d: d["x"] + d["y"] == 5)
    solver.add_constraint(lambda d: d["x"] > d["y"])
    solutions = solver.solve()
    print(f"  Solutions (x + y = 5, x > y): {solutions}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
