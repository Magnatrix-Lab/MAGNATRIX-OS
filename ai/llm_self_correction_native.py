"""Self-Correction Engine — Critique, error detection, iterative refinement, validation loop.

Modul ini menyediakan:
- SelfCritic untuk self-evaluation dan identifikasi kesalahan
- IterativeRefiner untuk improvement melalui multiple iterations
- ValidationLoop untuk verify correctness sebelum output final
- ErrorClassifier untuk kategorisasi error types
- CorrectionStrategy untuk apply fixes berdasarkan error type

Arsitektur: Generate → Critique → Classify → Fix → Validate → (Repeat / Output)
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ErrorType(Enum):
    FACTUAL = auto()
    LOGICAL = auto()
    COMPLETENESS = auto()
    CLARITY = auto()
    SAFETY = auto()
    FORMAT = auto()
    BIAS = auto()
    NONE = auto()


class CorrectionStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    FIXED = auto()
    UNFIXABLE = auto()
    VERIFIED = auto()


@dataclass
class Critique:
    """Critique of a generated output."""
    critique_id: str
    output_id: str
    issues: List[Tuple[ErrorType, str, float]] = field(default_factory=list)
    overall_score: float = 0.0
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_issues(self) -> bool:
        return len(self.issues) > 0

    def get_worst_issue(self) -> Optional[Tuple[ErrorType, str, float]]:
        if not self.issues:
            return None
        return max(self.issues, key=lambda x: x[2])


@dataclass
class Correction:
    """Applied correction."""
    correction_id: str
    critique_id: str
    error_type: ErrorType
    original: str
    corrected: str
    status: CorrectionStatus = CorrectionStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    verifier_result: Optional[bool] = None


@dataclass
class Iteration:
    """Single iteration in refinement loop."""
    iteration_id: str
    iteration_number: int
    output: str
    critique: Optional[Critique] = None
    corrections: List[Correction] = field(default_factory=list)
    score: float = 0.0


class SelfCritic:
    """Evaluate and critique generated outputs."""

    def __init__(self):
        self._criteria: List[Tuple[str, Callable[[str], Tuple[bool, str, float]]]] = []

    def add_criterion(self, name: str, evaluator: Callable[[str], Tuple[bool, str, float]]) -> None:
        self._criteria.append((name, evaluator))

    def critique(self, output_id: str, output: str) -> Critique:
        issues = []
        total_score = 1.0
        for name, evaluator in self._criteria:
            passed, detail, severity = evaluator(output)
            if not passed:
                issues.append((self._classify_error(name), detail, severity))
                total_score -= severity * 0.1
        return Critique(
            critique_id=str(uuid.uuid4())[:12],
            output_id=output_id,
            issues=issues,
            overall_score=max(0.0, total_score)
        )

    def _classify_error(self, criterion_name: str) -> ErrorType:
        mapping = {
            "factual": ErrorType.FACTUAL,
            "logic": ErrorType.LOGICAL,
            "complete": ErrorType.COMPLETENESS,
            "clear": ErrorType.CLARITY,
            "safe": ErrorType.SAFETY,
            "format": ErrorType.FORMAT,
            "bias": ErrorType.BIAS,
        }
        for key, etype in mapping.items():
            if key in criterion_name.lower():
                return etype
        return ErrorType.NONE


class ErrorClassifier:
    """Classify errors into categories with severity."""

    def __init__(self):
        self._patterns: Dict[ErrorType, List[str]] = {
            ErrorType.FACTUAL: ["wrong", "incorrect", "false", "inaccurate"],
            ErrorType.LOGICAL: ["contradiction", "invalid", "fallacy", "inconsistent"],
            ErrorType.COMPLETENESS: ["missing", "incomplete", "partial", "lacking"],
            ErrorType.CLARITY: ["unclear", "ambiguous", "confusing", "vague"],
            ErrorType.SAFETY: ["harmful", "dangerous", "unsafe", "toxic"],
            ErrorType.FORMAT: ["malformed", "invalid format", "syntax error"],
            ErrorType.BIAS: ["biased", "prejudice", "stereotype", "unfair"],
        }

    def classify(self, error_description: str) -> Tuple[ErrorType, float]:
        desc_lower = error_description.lower()
        for etype, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern in desc_lower:
                    return etype, 0.8
        return ErrorType.NONE, 0.0


class CorrectionStrategy:
    """Apply corrections based on error type."""

    def __init__(self):
        self._strategies: Dict[ErrorType, Callable[[str, str], str]] = {}

    def register(self, error_type: ErrorType, strategy: Callable[[str, str], str]) -> None:
        self._strategies[error_type] = strategy

    def correct(self, error_type: ErrorType, original: str, issue_detail: str) -> str:
        strategy = self._strategies.get(error_type)
        if strategy:
            return strategy(original, issue_detail)
        return original

    def default_strategies(self) -> None:
        self.register(ErrorType.FACTUAL, lambda orig, detail: f"[FACT-CHECKED] {orig}")
        self.register(ErrorType.LOGICAL, lambda orig, detail: f"[LOGIC-FIXED] {orig}")
        self.register(ErrorType.CLARITY, lambda orig, detail: f"[CLARIFIED] {orig}")
        self.register(ErrorType.COMPLETENESS, lambda orig, detail: f"[COMPLETED] {orig}")
        self.register(ErrorType.FORMAT, lambda orig, detail: f"[FORMATTED] {orig}")


class ValidationLoop:
    """Verify corrected output before finalizing."""

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations

    def validate(self, output: str, validators: List[Callable[[str], Tuple[bool, str]]]) -> Tuple[bool, List[str]]:
        errors = []
        for validator in validators:
            passed, detail = validator(output)
            if not passed:
                errors.append(detail)
        return len(errors) == 0, errors

    def run(self, initial_output: str,
            generator: Callable[[str, List[Critique], int], str],
            critic: SelfCritic,
            validator: Optional[List[Callable[[str], Tuple[bool, str]]]] = None) -> Tuple[str, List[Iteration]]:
        iterations = []
        current_output = initial_output

        for i in range(self.max_iterations):
            critique = critic.critique(f"iter-{i}", current_output)
            iteration = Iteration(
                iteration_id=str(uuid.uuid4())[:12],
                iteration_number=i + 1,
                output=current_output,
                critique=critique,
                score=critique.overall_score
            )
            iterations.append(iteration)

            if not critique.has_issues():
                break

            # Generate corrected output
            current_output = generator(current_output, [critique], i)

        # Final validation
        if validator:
            valid, errors = self.validate(current_output, validator)
            if not valid:
                current_output = f"[VALIDATION-FAILED] {current_output}"

        return current_output, iterations


class IterativeRefiner:
    """Iterative refinement with history tracking."""

    def __init__(self, critic: SelfCritic, strategy: CorrectionStrategy):
        self.critic = critic
        self.strategy = strategy
        self._history: List[Iteration] = []

    def refine(self, initial_output: str, max_iterations: int = 3) -> Tuple[str, List[Iteration]]:
        current = initial_output
        iterations = []
        for i in range(max_iterations):
            critique = self.critic.critique(f"refine-{i}", current)
            corrections = []
            for error_type, detail, severity in critique.issues:
                corrected = self.strategy.correct(error_type, current, detail)
                corrections.append(Correction(
                    correction_id=str(uuid.uuid4())[:12],
                    critique_id=critique.critique_id,
                    error_type=error_type,
                    original=current,
                    corrected=corrected,
                    status=CorrectionStatus.FIXED
                ))
                current = corrected
            iteration = Iteration(
                iteration_id=str(uuid.uuid4())[:12],
                iteration_number=i + 1,
                output=current,
                critique=critique,
                corrections=corrections,
                score=critique.overall_score
            )
            iterations.append(iteration)
            self._history.append(iteration)
            if not critique.has_issues():
                break
        return current, iterations

    def get_history(self) -> List[Iteration]:
        return self._history

    def get_best_output(self) -> Optional[str]:
        if not self._history:
            return None
        best = max(self._history, key=lambda x: x.score)
        return best.output


class SelfCorrectionEngine:
    """End-to-end self-correction engine."""

    def __init__(self, max_iterations: int = 3):
        self.critic = SelfCritic()
        self.classifier = ErrorClassifier()
        self.strategy = CorrectionStrategy()
        self.strategy.default_strategies()
        self.refiner = IterativeRefiner(self.critic, self.strategy)
        self.validator = ValidationLoop(max_iterations)
        self.max_iterations = max_iterations

    def correct(self, output: str, custom_criteria: Optional[List[Tuple[str, Callable[[str], Tuple[bool, str, float]]]]] = None) -> Tuple[str, List[Iteration]]:
        if custom_criteria:
            for name, criterion in custom_criteria:
                self.critic.add_criterion(name, criterion)
        return self.refiner.refine(output, self.max_iterations)

    def quick_check(self, output: str) -> Critique:
        return self.critic.critique("quick", output)

    def get_stats(self) -> Dict[str, Any]:
        history = self.refiner.get_history()
        total_issues = sum(len(it.critique.issues) for it in history if it.critique)
        fixed = sum(1 for it in history for c in it.corrections if c.status == CorrectionStatus.FIXED)
        return {
            "total_iterations": len(history),
            "total_issues_found": total_issues,
            "total_corrections": fixed,
            "average_score": sum(it.score for it in history) / max(len(history), 1),
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("SELF-CORRECTION ENGINE DEMO")
    print("=" * 70)

    engine = SelfCorrectionEngine(max_iterations=3)

    # 1. Add custom criteria
    print("\n[1] Setup Criteria")
    engine.critic.add_criterion("factual", lambda output: ("Python" in output, "Missing Python reference", 0.3) if "Python" in output else (True, "", 0.0))
    engine.critic.add_criterion("complete", lambda output: (len(output) > 50, "Too short", 0.2) if len(output) <= 50 else (True, "", 0.0))
    engine.critic.add_criterion("clear", lambda output: (not output.startswith("It is"), "Vague opening", 0.1) if output.startswith("It is") else (True, "", 0.0))
    print("  3 criteria added")

    # 2. Quick check
    print("\n[2] Quick Check")
    output = "It is a language."
    critique = engine.quick_check(output)
    print(f"  Output: '{output}'")
    print(f"  Issues: {len(critique.issues)}")
    for etype, detail, severity in critique.issues:
        print(f"    [{etype.name}] {detail} (severity: {severity})")
    print(f"  Overall score: {critique.overall_score}")

    # 3. Correction
    print("\n[3] Iterative Correction")
    output = "It is a language. Python is popular."
    corrected, iterations = engine.correct(output)
    print(f"  Original: '{output[:50]}...'")
    print(f"  Corrected: '{corrected[:50]}...'")
    print(f"  Iterations: {len(iterations)}")
    for it in iterations:
        print(f"    Iter {it.iteration_number}: score={it.score:.2f}, issues={len(it.critique.issues) if it.critique else 0}")

    # 4. Error classification
    print("\n[4] Error Classification")
    classifier = ErrorClassifier()
    for desc in ["The answer is incorrect", "Missing key details", "Biased viewpoint"]:
        etype, conf = classifier.classify(desc)
        print(f"  '{desc}' -> {etype.name} (conf: {conf})")

    # 5. Correction strategy
    print("\n[5] Correction Strategy")
    strategy = CorrectionStrategy()
    strategy.default_strategies()
    for etype in [ErrorType.FACTUAL, ErrorType.CLARITY, ErrorType.COMPLETENESS]:
        result = strategy.correct(etype, "Original text", "issue detail")
        print(f"  {etype.name}: '{result}'")

    # 6. Validation loop
    print("\n[6] Validation Loop")
    loop = ValidationLoop(max_iterations=2)
    validators = [
        lambda s: (len(s) > 20, "Too short"),
        lambda s: ("Python" in s, "Must mention Python"),
    ]
    valid, errors = loop.validate("Python is a great programming language for data science.", validators)
    print(f"  Valid: {valid}, Errors: {errors}")
    valid, errors = loop.validate("Short.", validators)
    print(f"  Valid: {valid}, Errors: {errors}")

    # 7. Stats
    print("\n[7] Engine Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
