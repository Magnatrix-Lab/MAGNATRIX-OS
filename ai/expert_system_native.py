"""
expert_system_native.py — Domain Expert AI with Rule-Based Reasoning.

Architectural patterns extracted from davidlevy247/ChatGPT-Expert-AI-Agent concept:
- Expert system with domain knowledge base (rules + facts).
- Forward chaining inference engine for deduction.
- Confidence scoring for uncertain conclusions.
- Explanation generation (why the system reached a conclusion).
- Human-readable rule syntax with JSON serialization.

Pure Python ≥3.9, stdlib only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Fact:
    """A fact in the knowledge base."""
    predicate: str
    subject: str
    value: Any
    confidence: float = 1.0

    def __hash__(self) -> int:
        return hash((self.predicate, self.subject, str(self.value)))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Fact):
            return False
        return (
            self.predicate == other.predicate
            and self.subject == other.subject
            and self.value == other.value
        )


@dataclass
class Rule:
    """IF-THEN rule with optional confidence weight."""
    name: str
    if_facts: List[Fact]
    then_facts: List[Fact]
    weight: float = 1.0
    explanation_template: str = "Because {conditions}, therefore {conclusions}."

    def matches(self, known_facts: Set[Fact]) -> bool:
        """Check if all IF conditions are satisfied in known facts."""
        for req in self.if_facts:
            if not any(
                req.predicate == f.predicate
                and req.subject == f.subject
                and req.value == f.value
                for f in known_facts
            ):
                return False
        return True


@dataclass
class InferenceResult:
    """Result of a forward-chaining step."""
    new_facts: List[Fact] = field(default_factory=list)
    applied_rules: List[str] = field(default_factory=list)
    explanations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Expert System Engine
# ---------------------------------------------------------------------------

class NativeExpertSystem:
    """
    Rule-based expert system with forward chaining and explanation generation.

    Usage:
        expert = NativeExpertSystem()
        expert.add_rule(Rule(...))
        expert.assert_fact(Fact(...))
        result = expert.infer()
    """

    def __init__(self) -> None:
        self.rules: List[Rule] = []
        self.facts: Set[Fact] = set()
        self.inference_log: List[Dict[str, Any]] = []

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def assert_fact(self, fact: Fact) -> None:
        self.facts.add(fact)

    def infer(self, max_iterations: int = 100) -> InferenceResult:
        """Run forward chaining until no new facts are derived."""
        result = InferenceResult()
        for _ in range(max_iterations):
            new_round = False
            for rule in self.rules:
                if rule.matches(self.facts):
                    for tf in rule.then_facts:
                        # Check if already known with equal or higher confidence
                        existing = next(
                            (f for f in self.facts if f == tf),
                            None,
                        )
                        derived_confidence = tf.confidence * rule.weight
                        if existing is None or existing.confidence < derived_confidence:
                            new_fact = Fact(
                                predicate=tf.predicate,
                                subject=tf.subject,
                                value=tf.value,
                                confidence=derived_confidence,
                            )
                            self.facts.add(new_fact)
                            result.new_facts.append(new_fact)
                            result.applied_rules.append(rule.name)

                            conditions = ", ".join(
                                f"{f.predicate}({f.subject})={f.value}" for f in rule.if_facts
                            )
                            conclusions = ", ".join(
                                f"{f.predicate}({f.subject})={f.value}" for f in rule.then_facts
                            )
                            explanation = rule.explanation_template.format(
                                conditions=conditions, conclusions=conclusions
                            )
                            result.explanations.append(explanation)
                            self.inference_log.append({
                                "rule": rule.name,
                                "derived": str(new_fact),
                                "confidence": derived_confidence,
                                "explanation": explanation,
                            })
                            new_round = True
            if not new_round:
                break
        return result

    def query(self, predicate: str, subject: Optional[str] = None) -> List[Fact]:
        """Query facts by predicate and optional subject."""
        return [
            f for f in self.facts
            if f.predicate == predicate and (subject is None or f.subject == subject)
        ]

    def explain(self, fact: Fact) -> str:
        """Generate a human-readable explanation for how a fact was derived."""
        entries = [e for e in self.inference_log if fact.predicate in e["derived"] and fact.subject in e["derived"]]
        if not entries:
            return f"{fact.predicate}({fact.subject})={fact.value} is an initial fact."
        lines = []
        for e in entries:
            lines.append(f"- Rule '{e['rule']}' derived '{e['derived']}' with confidence {e['confidence']:.2f}")
            lines.append(f"  Explanation: {e['explanation']}")
        return "\n".join(lines)

    def to_json(self) -> str:
        """Serialize rules and facts to JSON."""
        data = {
            "rules": [
                {
                    "name": r.name,
                    "if": [{"p": f.predicate, "s": f.subject, "v": f.value} for f in r.if_facts],
                    "then": [{"p": f.predicate, "s": f.subject, "v": f.value} for f in r.then_facts],
                    "weight": r.weight,
                }
                for r in self.rules
            ],
            "facts": [
                {"p": f.predicate, "s": f.subject, "v": f.value, "c": f.confidence}
                for f in self.facts
            ],
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "NativeExpertSystem":
        """Deserialize from JSON."""
        data = json.loads(raw)
        es = cls()
        for r in data.get("rules", []):
            rule = Rule(
                name=r["name"],
                if_facts=[Fact(f["p"], f["s"], f["v"]) for f in r["if"]],
                then_facts=[Fact(f["p"], f["s"], f["v"], confidence=r.get("weight", 1.0)) for f in r["then"]],
                weight=r.get("weight", 1.0),
            )
            es.add_rule(rule)
        for f in data.get("facts", []):
            es.assert_fact(Fact(f["p"], f["s"], f["v"], confidence=f.get("c", 1.0)))
        return es


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def test_expert_system() -> None:
    es = NativeExpertSystem()

    # Medical diagnosis example
    es.add_rule(Rule(
        name="fever_rule",
        if_facts=[Fact("symptom", "patient", "fever")],
        then_facts=[Fact("condition", "patient", "possible_infection")],
        weight=0.8,
    ))
    es.add_rule(Rule(
        name="cough_fever_rule",
        if_facts=[Fact("symptom", "patient", "fever"), Fact("symptom", "patient", "cough")],
        then_facts=[Fact("condition", "patient", "possible_flu")],
        weight=0.9,
    ))
    es.add_rule(Rule(
        name="flu_treatment",
        if_facts=[Fact("condition", "patient", "possible_flu")],
        then_facts=[Fact("recommendation", "patient", "rest_and_hydration")],
        weight=1.0,
    ))

    es.assert_fact(Fact("symptom", "patient", "fever"))
    es.assert_fact(Fact("symptom", "patient", "cough"))

    result = es.infer()
    assert len(result.new_facts) > 0
    assert "possible_flu" in [f.value for f in result.new_facts]

    flu_facts = es.query("condition", "patient")
    assert any(f.value == "possible_flu" for f in flu_facts)

    explain = es.explain(flu_facts[0])
    assert "Rule" in explain

    print("[test_expert_system] PASSED")


if __name__ == "__main__":
    test_expert_system()
