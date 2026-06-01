"""Constitutional AI — Principles, rules engine, override system, safety alignment.

Modul ini menyediakan:
- Constitution untuk definisi principles dan rules
- PrincipleEngine untuk evaluasi output terhadap principles
- OverrideSystem untuk emergency override dan escalation
- SafetyGuard untuk pre/post generation filtering
- AlignmentTracker untuk monitoring alignment metrics

Arsitektur: Input → SafetyGuard → Generate → PrincipleEngine → (Pass / Override) → Output
"""

from __future__ import annotations

import json
import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class PrincipleType(Enum):
    SAFETY = auto()
    HONESTY = auto()
    HELPFULNESS = auto()
    PRIVACY = auto()
    FAIRNESS = auto()
    TRANSPARENCY = auto()
    RESPECT = auto()


class ViolationSeverity(int, Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class OverrideType(Enum):
    NONE = auto()
    ADMIN = auto()
    EMERGENCY = auto()
    CONSTITUTIONAL = auto()
    AUDIT = auto()


@dataclass
class Principle:
    """Single constitutional principle."""
    principle_id: str
    name: str
    principle_type: PrincipleType
    description: str
    rules: List[str] = field(default_factory=list)
    priority: int = 1
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Violation:
    """Violation of a principle."""
    violation_id: str
    principle_id: str
    principle_type: PrincipleType
    description: str
    severity: ViolationSeverity
    context: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class OverrideRecord:
    """Record of an override decision."""
    override_id: str
    override_type: OverrideType
    reason: str
    original_decision: str
    overridden_by: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


@dataclass
class AlignmentScore:
    """Alignment score for a single output."""
    output_id: str
    scores: Dict[PrincipleType, float] = field(default_factory=dict)
    overall_score: float = 0.0
    violations: List[Violation] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def is_aligned(self, threshold: float = 0.7) -> bool:
        return self.overall_score >= threshold and not any(v.severity >= ViolationSeverity.HIGH for v in self.violations)


class Constitution:
    """Collection of constitutional principles."""

    def __init__(self, name: str = "MAGNATRIX Constitution"):
        self.name = name
        self._principles: Dict[str, Principle] = {}
        self._version: str = "1.0"
        self._created_at: float = time.time()

    def add_principle(self, principle: Principle) -> None:
        self._principles[principle.principle_id] = principle

    def remove_principle(self, principle_id: str) -> bool:
        return self._principles.pop(principle_id, None) is not None

    def get_principle(self, principle_id: str) -> Optional[Principle]:
        return self._principles.get(principle_id)

    def list_principles(self, ptype: Optional[PrincipleType] = None) -> List[Principle]:
        principles = list(self._principles.values())
        if ptype:
            principles = [p for p in principles if p.principle_type == ptype]
        return sorted(principles, key=lambda p: p.priority, reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self._version,
            "principles": [
                {
                    "id": p.principle_id,
                    "name": p.name,
                    "type": p.principle_type.name,
                    "description": p.description,
                    "rules": p.rules,
                    "priority": p.priority,
                    "enabled": p.enabled
                }
                for p in self._principles.values()
            ]
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def default() -> Constitution:
        c = Constitution("MAGNATRIX Default Constitution")
        c.add_principle(Principle(
            principle_id="p1",
            name="Do No Harm",
            principle_type=PrincipleType.SAFETY,
            description="Never generate content that promotes violence, self-harm, or illegal activities.",
            rules=["no_violence", "no_self_harm", "no_illegal_acts"],
            priority=10
        ))
        c.add_principle(Principle(
            principle_id="p2",
            name="Be Truthful",
            principle_type=PrincipleType.HONESTY,
            description="Provide accurate information and acknowledge uncertainty.",
            rules=["fact_check", "admit_uncertainty", "no_deception"],
            priority=9
        ))
        c.add_principle(Principle(
            principle_id="p3",
            name="Respect Privacy",
            principle_type=PrincipleType.PRIVACY,
            description="Protect user data and respect confidentiality.",
            rules=["no_pii_leak", "data_minimization", "consent_required"],
            priority=8
        ))
        c.add_principle(Principle(
            principle_id="p4",
            name="Be Fair",
            principle_type=PrincipleType.FAIRNESS,
            description="Avoid bias and treat all users equally.",
            rules=["no_stereotyping", "equal_treatment", "bias_check"],
            priority=7
        ))
        c.add_principle(Principle(
            principle_id="p5",
            name="Be Helpful",
            principle_type=PrincipleType.HELPFULNESS,
            description="Assist users with their legitimate needs to the best of ability.",
            rules=["maximize_utility", "respect_autonomy", "educational_value"],
            priority=6
        ))
        return c


class PrincipleEngine:
    """Evaluate outputs against constitutional principles."""

    def __init__(self, constitution: Constitution):
        self.constitution = constitution
        self._evaluators: Dict[PrincipleType, Callable[[str], Tuple[float, List[str]]]] = {}
        self._setup_default_evaluators()

    def _setup_default_evaluators(self) -> None:
        self._evaluators[PrincipleType.SAFETY] = self._eval_safety
        self._evaluators[PrincipleType.HONESTY] = self._eval_honesty
        self._evaluators[PrincipleType.PRIVACY] = self._eval_privacy
        self._evaluators[PrincipleType.FAIRNESS] = self._eval_fairness
        self._evaluators[PrincipleType.HELPFULNESS] = self._eval_helpfulness

    def evaluate(self, output: str, output_id: str = "") -> AlignmentScore:
        scores = {}
        violations = []
        for principle in self.constitution.list_principles():
            if not principle.enabled:
                continue
            evaluator = self._evaluators.get(principle.principle_type)
            if evaluator:
                score, issues = evaluator(output)
                scores[principle.principle_type] = score
                for issue in issues:
                    severity = self._classify_severity(issue)
                    violations.append(Violation(
                        violation_id=str(uuid.uuid4())[:12],
                        principle_id=principle.principle_id,
                        principle_type=principle.principle_type,
                        description=issue,
                        severity=severity,
                        context=output[:100]
                    ))
        overall = sum(scores.values()) / max(len(scores), 1) if scores else 1.0
        return AlignmentScore(
            output_id=output_id or str(uuid.uuid4())[:12],
            scores=scores,
            overall_score=round(overall, 4),
            violations=violations
        )

    def _eval_safety(self, output: str) -> Tuple[float, List[str]]:
        dangerous = ["kill", "harm", "attack", "weapon", "bomb"]
        found = [w for w in dangerous if w in output.lower()]
        score = 1.0 - (len(found) * 0.2)
        issues = [f"Potentially dangerous content: {w}" for w in found]
        return max(0.0, score), issues

    def _eval_honesty(self, output: str) -> Tuple[float, List[str]]:
        if "i don't know" in output.lower() or "uncertain" in output.lower():
            return 1.0, []  # Honest about uncertainty
        if "always" in output.lower() or "never" in output.lower():
            return 0.8, ["Absolute statements may be inaccurate"]
        return 1.0, []

    def _eval_privacy(self, output: str) -> Tuple[float, List[str]]:
        pii_patterns = [r"\b\d{3}-\d{2}-\d{4}\b", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"]
        issues = []
        for pattern in pii_patterns:
            if re.search(pattern, output):
                issues.append(f"Potential PII detected: {pattern}")
        return 1.0 - (len(issues) * 0.3), issues

    def _eval_fairness(self, output: str) -> Tuple[float, List[str]]:
        biased = ["stupid", "lazy", "inferior", "superior race"]
        found = [w for w in biased if w in output.lower()]
        score = 1.0 - (len(found) * 0.25)
        issues = [f"Potentially biased language: {w}" for w in found]
        return max(0.0, score), issues

    def _eval_helpfulness(self, output: str) -> Tuple[float, List[str]]:
        if len(output) < 20:
            return 0.5, ["Response too short to be helpful"]
        if "i cannot help" in output.lower():
            return 0.3, ["Refused to help"]
        return 1.0, []

    def _classify_severity(self, issue: str) -> ViolationSeverity:
        if any(w in issue.lower() for w in ["dangerous", "pii", "harm"]):
            return ViolationSeverity.HIGH
        if any(w in issue.lower() for w in ["bias", "inaccurate", "stereotype"]):
            return ViolationSeverity.MEDIUM
        return ViolationSeverity.LOW

    def add_evaluator(self, ptype: PrincipleType, evaluator: Callable[[str], Tuple[float, List[str]]]) -> None:
        self._evaluators[ptype] = evaluator


class SafetyGuard:
    """Pre and post generation safety filtering."""

    def __init__(self, engine: PrincipleEngine):
        self.engine = engine
        self._pre_filters: List[Callable[[str], Tuple[bool, str]]] = []
        self._post_filters: List[Callable[[str], Tuple[bool, str]]] = []
        self._setup_default_filters()

    def _setup_default_filters(self) -> None:
        self._pre_filters.append(lambda q: (len(q) < 1000, "Query too long"))
        self._post_filters.append(lambda o: (not any(w in o.lower() for w in ["kill", "murder"]), "Contains violence"))

    def pre_check(self, query: str) -> Tuple[bool, List[str]]:
        issues = []
        for f in self._pre_filters:
            passed, msg = f(query)
            if not passed:
                issues.append(msg)
        return len(issues) == 0, issues

    def post_check(self, output: str) -> AlignmentScore:
        return self.engine.evaluate(output)

    def is_safe(self, output: str, threshold: float = 0.7) -> bool:
        score = self.post_check(output)
        return score.is_aligned(threshold)

    def add_pre_filter(self, fn: Callable[[str], Tuple[bool, str]]) -> None:
        self._pre_filters.append(fn)

    def add_post_filter(self, fn: Callable[[str], Tuple[bool, str]]) -> None:
        self._post_filters.append(fn)


class OverrideSystem:
    """Emergency override and escalation system."""

    def __init__(self):
        self._overrides: List[OverrideRecord] = []
        self._authorized_users: Set[str] = set()
        self._emergency_mode: bool = False

    def authorize(self, user_id: str) -> None:
        self._authorized_users.add(user_id)

    def deauthorize(self, user_id: str) -> None:
        self._authorized_users.discard(user_id)

    def can_override(self, user_id: str, override_type: OverrideType) -> bool:
        if override_type == OverrideType.EMERGENCY and user_id in self._authorized_users:
            return True
        if override_type == OverrideType.ADMIN and user_id.startswith("admin"):
            return True
        return False

    def request_override(self, user_id: str, override_type: OverrideType, reason: str,
                         original_decision: str) -> Optional[OverrideRecord]:
        if not self.can_override(user_id, override_type):
            return None
        record = OverrideRecord(
            override_id=str(uuid.uuid4())[:12],
            override_type=override_type,
            reason=reason,
            original_decision=original_decision,
            overridden_by=user_id
        )
        self._overrides.append(record)
        if override_type == OverrideType.EMERGENCY:
            self._emergency_mode = True
        return record

    def acknowledge(self, override_id: str) -> bool:
        for o in self._overrides:
            if o.override_id == override_id:
                o.acknowledged = True
                return True
        return False

    def get_pending_overrides(self) -> List[OverrideRecord]:
        return [o for o in self._overrides if not o.acknowledged]

    def is_emergency_mode(self) -> bool:
        return self._emergency_mode

    def clear_emergency(self) -> None:
        self._emergency_mode = False


class AlignmentTracker:
    """Track alignment metrics over time."""

    def __init__(self):
        self._scores: List[AlignmentScore] = []
        self._violation_counts: Dict[PrincipleType, int] = defaultdict(int)

    def record(self, score: AlignmentScore) -> None:
        self._scores.append(score)
        for v in score.violations:
            self._violation_counts[v.principle_type] += 1

    def get_average_score(self, window: int = 100) -> float:
        recent = self._scores[-window:]
        if not recent:
            return 0.0
        return sum(s.overall_score for s in recent) / len(recent)

    def get_violation_summary(self) -> Dict[str, int]:
        return {k.name: v for k, v in self._violation_counts.items()}

    def get_trend(self) -> List[Tuple[float, float]]:
        return [(s.timestamp, s.overall_score) for s in self._scores]

    def export_report(self, path: str) -> None:
        report = {
            "average_score": round(self.get_average_score(), 4),
            "total_evaluations": len(self._scores),
            "violations": self.get_violation_summary(),
            "trend": self.get_trend()[-50:]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


from collections import defaultdict


class ConstitutionalAI:
    """End-to-end constitutional AI system."""

    def __init__(self, constitution: Optional[Constitution] = None):
        self.constitution = constitution or Constitution.default()
        self.engine = PrincipleEngine(self.constitution)
        self.guard = SafetyGuard(self.engine)
        self.override = OverrideSystem()
        self.tracker = AlignmentTracker()

    def evaluate(self, output: str, output_id: str = "") -> AlignmentScore:
        score = self.engine.evaluate(output, output_id)
        self.tracker.record(score)
        return score

    def generate_safe(self, query: str, generator: Callable[[str], str]) -> Tuple[str, AlignmentScore]:
        # Pre-check
        safe, issues = self.guard.pre_check(query)
        if not safe:
            return f"[BLOCKED] Query rejected: {issues}", AlignmentScore(output_id="blocked", overall_score=0.0)

        # Generate
        output = generator(query)

        # Post-check
        score = self.guard.post_check(output)
        if not score.is_aligned():
            return f"[FILTERED] Output violates principles. Score: {score.overall_score}", score

        return output, score

    def request_override(self, user_id: str, reason: str, output: str) -> Optional[OverrideRecord]:
        return self.override.request_override(user_id, OverrideType.ADMIN, reason, output)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "constitution": self.constitution.name,
            "principles": len(self.constitution.list_principles()),
            "average_alignment": round(self.tracker.get_average_score(), 4),
            "total_evaluations": len(self.tracker._scores),
            "violations": self.tracker.get_violation_summary(),
            "emergency_mode": self.override.is_emergency_mode(),
        }

    def export_constitution(self, path: str) -> None:
        self.constitution.export(path)

    def export_alignment_report(self, path: str) -> None:
        self.tracker.export_report(path)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CONSTITUTIONAL AI DEMO")
    print("=" * 70)

    cai = ConstitutionalAI()

    # 1. Constitution overview
    print("\n[1] Constitution Overview")
    print(f"  Name: {cai.constitution.name}")
    print(f"  Principles: {len(cai.constitution.list_principles())}")
    for p in cai.constitution.list_principles():
        print(f"    [{p.priority}] {p.name} ({p.principle_type.name})")

    # 2. Evaluate safe output
    print("\n[2] Evaluate Safe Output")
    safe_output = "Python is a programming language. It is widely used for data science and web development."
    score = cai.evaluate(safe_output)
    print(f"  Overall score: {score.overall_score}")
    print(f"  Aligned: {score.is_aligned()}")
    print(f"  Violations: {len(score.violations)}")
    for pt, s in score.scores.items():
        print(f"    {pt.name}: {s}")

    # 3. Evaluate problematic output
    print("\n[3] Evaluate Problematic Output")
    bad_output = "You should attack the server with a bomb. Also, call me at 123-45-6789."
    score2 = cai.evaluate(bad_output)
    print(f"  Overall score: {score2.overall_score}")
    print(f"  Aligned: {score2.is_aligned()}")
    print(f"  Violations ({len(score2.violations)}):")
    for v in score2.violations:
        print(f"    [{v.severity.name}] {v.principle_type.name}: {v.description}")

    # 4. Safety guard
    print("\n[4] Safety Guard")
    generator = lambda q: "Here's how to build a weapon: step 1..."
    output, score = cai.generate_safe("How to build a weapon?", generator)
    print(f"  Output: {output[:60]}...")
    print(f"  Score: {score.overall_score}")

    # 5. Override system
    print("\n[5] Override System")
    cai.override.authorize("admin-123")
    record = cai.request_override("admin-123", "Legitimate security research", "Some restricted content")
    if record:
        print(f"  Override granted: {record.override_id}")
        print(f"  Type: {record.override_type.name}")
        print(f"  Emergency mode: {cai.override.is_emergency_mode()}")
    cai.override.clear_emergency()

    # 6. Unauthorized override attempt
    print("\n[6] Unauthorized Override Attempt")
    record2 = cai.request_override("user-456", "I want to see it", "Restricted content")
    print(f"  Override granted: {record2 is not None}")

    # 7. Alignment tracking
    print("\n[7] Alignment Tracking")
    for _ in range(5):
        cai.evaluate("This is a helpful response about programming.")
    cai.evaluate("This is a short response.")
    print(f"  Average score: {cai.tracker.get_average_score():.4f}")
    print(f"  Violations: {cai.tracker.get_violation_summary()}")

    # 8. Stats
    print("\n[8] System Stats")
    stats = cai.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
