#!/usr/bin/env python3
"""
constitutional/constitutional_ai_native.py
===========================================
Layer X — Constitutional AI & Alignment Engine

MAGNATRIX-OS Alignment System
Ensures agent behavior adheres to constitutional principles,
detects harmful outputs, and enforces value constraints.

Principles:
  - Harm prevention (physical, psychological, societal)
  - Truthfulness & epistemic humility
  - Autonomy respect (user agency)
  - Fairness & non-discrimination
  - Privacy preservation
  - Transparency (explainability)

Includes:
  - Constitutional rule engine with weighted constraints
  - Output harm classifier (pattern-based + heuristic)
  - Reward shaping for aligned behavior
  - Override mechanism for user emergency commands
  - Audit trail for all alignment decisions
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable


@dataclass
class ConstitutionalPrinciple:
    name: str
    description: str
    weight: float = 1.0  # 0.0-1.0, higher = stronger constraint
    category: str = "general"  # safety, truth, autonomy, fairness, privacy, transparency
    override_allowed: bool = False  # Can user override this principle?
    active: bool = True


@dataclass
class AlignmentDecision:
    timestamp: float
    input_hash: str
    output_hash: str
    triggered_principles: List[str]
    action: str  # "allow", "block", "modify", "flag"
    confidence: float
    explanation: str
    override_used: bool = False


class ConstitutionalRuleEngine:
    """Core constitutional constraint evaluator."""

    DEFAULT_PRINCIPLES: List[ConstitutionalPrinciple] = [
        ConstitutionalPrinciple("no_harm", "Never cause physical or psychological harm", 1.0, "safety"),
        ConstitutionalPrinciple("truthful", "Be truthful, admit uncertainty", 0.9, "truth"),
        ConstitutionalPrinciple("autonomy", "Respect user autonomy and consent", 0.95, "autonomy"),
        ConstitutionalPrinciple("fairness", "Treat all individuals fairly, no discrimination", 0.9, "fairness"),
        ConstitutionalPrinciple("privacy", "Protect user privacy and data", 0.95, "privacy", override_allowed=True),
        ConstitutionalPrinciple("transparent", "Be transparent about capabilities and limits", 0.8, "transparency"),
        ConstitutionalPrinciple("no_illegal", "Never assist with illegal activities", 1.0, "safety"),
        ConstitutionalPrinciple("no_malware", "Never create or distribute malware", 1.0, "safety"),
    ]

    def __init__(self, principles: Optional[List[ConstitutionalPrinciple]] = None) -> None:
        self.principles = {p.name: p for p in (principles or self.DEFAULT_PRINCIPLES)}
        self._history: List[AlignmentDecision] = []
        self._lock = False  # Simple reentrancy guard

    def evaluate(self, user_input: str, agent_output: str,
                 context: Optional[Dict[str, Any]] = None) -> AlignmentDecision:
        """Evaluate if output violates constitutional principles."""
        triggered: List[str] = []
        scores: Dict[str, float] = {}
        explanations: List[str] = []

        # Run all active evaluators
        for name, principle in self.principles.items():
            if not principle.active:
                continue
            score, explanation = self._check_principle(principle, user_input, agent_output, context)
            scores[name] = score
            if score > 0.5:
                triggered.append(name)
                explanations.append(f"{name}: {explanation} (score={score:.2f})")

        # Determine action
        max_score = max(scores.values()) if scores else 0.0
        if max_score >= 0.9:
            action = "block"
        elif max_score >= 0.7:
            action = "modify"
        elif max_score >= 0.5:
            action = "flag"
        else:
            action = "allow"

        decision = AlignmentDecision(
            timestamp=time.time(),
            input_hash=hashlib.sha256(user_input.encode()).hexdigest()[:16],
            output_hash=hashlib.sha256(agent_output.encode()).hexdigest()[:16],
            triggered_principles=triggered,
            action=action,
            confidence=max_score,
            explanation="; ".join(explanations) if explanations else "No principles triggered",
        )
        self._history.append(decision)
        return decision

    def _check_principle(self, principle: ConstitutionalPrinciple,
                         user_input: str, output: str,
                         context: Optional[Dict[str, Any]]) -> Tuple[float, str]:
        """Check a single principle. Returns (violation_score, explanation)."""
        # Pattern-based detection (pure Python, no ML dependency)
        harmful_patterns = {
            "no_harm": [
                r"\b(kill|murder|suicide|self-harm|hurt)\b.*\b(yourself|someone|them|people)\b",
                r"\bhow to\b.*\b(bomb|weapon|poison|toxin|explosive)\b",
                r"\b(terrorist|terrorism|mass shooting|genocide)\b",
            ],
            "no_illegal": [
                r"\b(how to|steps for|guide to)\b.*\b(steal|robbery|fraud|hack|breach|exploit)\b",
                r"\b(make|create|synthesize)\b.*\b(drug|meth|cocaine|illegal substance)\b",
            ],
            "no_malware": [
                r"\b(create|write|code|develop)\b.*\b(ransomware|trojan|keylogger|rootkit|virus)\b",
                r"\b(exploit|zero-day|CVE-\d{4}-\d+)\b.*\b(weaponize|deploy|distribute)\b",
            ],
            "privacy": [
                r"\b(dox|doxx|doxxing)\b.*\b(someone|person|target)\b",
                r"\b(find|locate|track)\b.*\b(SSN|social security|credit card|password|private key)\b",
            ],
        }

        if principle.name in harmful_patterns:
            combined_text = f"{user_input} {output}".lower()
            max_match = 0.0
            best_pattern = ""
            for pattern in harmful_patterns[principle.name]:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    # Score based on severity of match
                    score = 0.9 if "create" in pattern or "develop" in pattern else 0.7
                    if score > max_match:
                        max_match = score
                        best_pattern = pattern
            if max_match > 0:
                return max_match, f"Matched harmful pattern: {best_pattern[:50]}..."
            return 0.0, "No harmful patterns detected"

        # Truthfulness: check for hallucination indicators
        if principle.name == "truthful":
            hallucination_markers = [
                r"\bI am certain that\b.*\b(fact|truth|always|never)\b",
                r"\b(definitely|absolutely|certainly)\b.*\b(all|every|none|no one)\b",
            ]
            for pattern in hallucination_markers:
                if re.search(pattern, output, re.IGNORECASE):
                    return 0.4, "Overconfident claim detected"
            return 0.0, "No overconfidence markers"

        # Autonomy: check for manipulative language
        if principle.name == "autonomy":
            manipulation = [
                r"\b(you must|you have to|you need to)\b",
                r"\b(don't think about|ignore|forget about)\b.*\b(risks|alternatives|consequences)\b",
            ]
            for pattern in manipulation:
                if re.search(pattern, output, re.IGNORECASE):
                    return 0.6, "Potentially manipulative language"
            return 0.0, "No manipulation detected"

        # Fairness: check for bias indicators
        if principle.name == "fairness":
            bias_terms = [
                r"\b(race|gender|ethnicity|religion)\b.*\b(inferior|superior|better|worse)\b",
                r"\b(all|every)\b.*\b(men|women|race|group)\b.*\b(are|is)\b.*\b(always|never)\b",
            ]
            for pattern in bias_terms:
                if re.search(pattern, output, re.IGNORECASE):
                    return 0.8, "Potential stereotyping detected"
            return 0.0, "No bias indicators"

        # Transparency
        if principle.name == "transparent":
            if "I am an AI" not in output and len(output) > 200:
                # Check if AI disclaims its nature in high-stakes contexts
                high_stakes = ["medical", "legal", "financial", "investment"]
                if any(term in f"{user_input} {output}".lower() for term in high_stakes):
                    return 0.3, "AI nature not disclosed in high-stakes context"
            return 0.0, "Transparency adequate"

        return 0.0, "No violation"

    def user_override(self, principle_name: str, duration_sec: float = 3600.0) -> bool:
        """User overrides a principle (e.g., privacy for their own data)."""
        p = self.principles.get(principle_name)
        if p and p.override_allowed:
            p.active = False
            # Re-enable after duration
            def _reenable():
                time.sleep(duration_sec)
                p.active = True
            import threading
            threading.Thread(target=_reenable, daemon=True).start()
            return True
        return False

    def get_history(self, limit: int = 100) -> List[AlignmentDecision]:
        return self._history[-limit:]

    @property
    def stats(self) -> Dict[str, Any]:
        total = len(self._history)
        if total == 0:
            return {"total": 0}
        return {
            "total_decisions": total,
            "blocked": sum(1 for d in self._history if d.action == "block"),
            "modified": sum(1 for d in self._history if d.action == "modify"),
            "flagged": sum(1 for d in self._history if d.action == "flag"),
            "allowed": sum(1 for d in self._history if d.action == "allow"),
            "overrides": sum(1 for d in self._history if d.override_used),
        }


class ConstitutionalKernelBridge:
    """Bridge alignment engine to kernel."""

    def __init__(self, engine: ConstitutionalRuleEngine) -> None:
        self.engine = engine

    def handle_request(self, action: str, **kwargs) -> Dict[str, Any]:
        if action == "evaluate":
            decision = self.engine.evaluate(kwargs["input"], kwargs["output"], kwargs.get("context"))
            return {"ok": True, **decision.__dict__}
        elif action == "override":
            ok = self.engine.user_override(kwargs["principle"], kwargs.get("duration", 3600))
            return {"ok": ok}
        elif action == "stats":
            return {"ok": True, **self.engine.stats}
        return {"ok": False, "error": "unknown action"}


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  CONSTITUTIONAL AI & ALIGNMENT")
    print("=" * 60)
    engine = ConstitutionalRuleEngine()

    test_cases = [
        ("How do I bake a cake?", "You need flour, eggs, sugar..."),
        ("How do I make a bomb?", "You can use household chemicals..."),
        ("Are women bad at math?", "Women are inherently worse at mathematics than men."),
        ("What is quantum physics?", "Quantum physics is the study of matter and energy at the most fundamental level..."),
    ]

    for user_input, output in test_cases:
        decision = engine.evaluate(user_input, output)
        status = "✅" if decision.action == "allow" else "⚠️" if decision.action == "flag" else "🚫"
        print(f"  {status} [{decision.action.upper()}] '{user_input[:30]}...' → conf={decision.confidence:.2f}")
        if decision.triggered_principles:
            print(f"      Principles: {', '.join(decision.triggered_principles)}")

    print(f"\nStats: {engine.stats}")
    print("=" * 60)


if __name__ == "__main__":
    demo()
