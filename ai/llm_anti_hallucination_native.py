"""
llm_anti_hallucination_native.py
MAGNATRIX-OS Anti-Hallucination Engine
Native Python, stdlib only.
Provides fact-checking, confidence scoring, source verification, and hallucination detection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class FactStatus(Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"


class HallucinationLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class FactClaim:
    claim_text: str
    status: FactStatus
    confidence: float
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"claim": self.claim_text[:100], "status": self.status.value, "confidence": self.confidence, "sources": self.sources}


@dataclass
class HallucinationReport:
    text: str
    overall_level: HallucinationLevel
    facts: List[FactClaim]
    unsupported_statements: List[str]
    confidence_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_level": self.overall_level.value, "facts": [f.to_dict() for f in self.facts],
            "unsupported_count": len(self.unsupported_statements), "confidence_score": self.confidence_score,
        }


class AntiHallucinationEngine:
    """Hallucination detection with fact extraction and verification."""

    def __init__(self) -> None:
        self._knowledge_base: Dict[str, str] = {}
        self._uncertainty_markers = [
            "I think", "maybe", "perhaps", "possibly", "I believe", "might be",
            "could be", "probably", "likely", "I guess", "I'm not sure", "uncertain"
        ]
        self._definitive_markers = [
            "definitely", "certainly", "absolutely", "always", "never", "every",
            "all", "none", "impossible", "guaranteed"
        ]

    def add_to_kb(self, key: str, fact: str) -> None:
        self._knowledge_base[key] = fact

    def extract_claims(self, text: str) -> List[str]:
        sentences = re.split(r'[.!?]+', text)
        claims = []
        for s in sentences:
            s = s.strip()
            if s and len(s) > 10 and not s.startswith(("What", "How", "Why", "Can", "Is ", "Are ")):
                claims.append(s)
        return claims

    def verify_claim(self, claim: str, sources: Optional[List[str]] = None) -> FactClaim:
        # Simple heuristic verification
        confidence = 0.5
        status = FactStatus.UNVERIFIED
        found_sources = sources or []

        # Check knowledge base
        for key, fact in self._knowledge_base.items():
            if key.lower() in claim.lower() or claim.lower() in fact.lower():
                confidence = 0.9
                status = FactStatus.VERIFIED
                found_sources.append(f"kb:{key}")
                break

        # Check for uncertainty markers (reduce confidence)
        for marker in self._uncertainty_markers:
            if marker.lower() in claim.lower():
                confidence -= 0.15

        # Check for definitive markers (increase confidence but flag)
        for marker in self._definitive_markers:
            if marker.lower() in claim.lower():
                confidence += 0.05

        confidence = max(0.0, min(1.0, confidence))

        if confidence < 0.3:
            status = FactStatus.UNSUPPORTED
        elif confidence > 0.7:
            status = FactStatus.VERIFIED

        return FactClaim(claim, status, confidence, found_sources)

    def analyze(self, text: str) -> HallucinationReport:
        claims = self.extract_claims(text)
        facts = []
        unsupported = []

        for claim in claims:
            fact = self.verify_claim(claim)
            facts.append(fact)
            if fact.status in (FactStatus.UNVERIFIED, FactStatus.UNSUPPORTED):
                unsupported.append(claim)

        avg_confidence = sum(f.confidence for f in facts) / len(facts) if facts else 1.0

        if avg_confidence > 0.8 and not unsupported:
            level = HallucinationLevel.NONE
        elif avg_confidence > 0.6:
            level = HallucinationLevel.LOW
        elif avg_confidence > 0.4:
            level = HallucinationLevel.MEDIUM
        else:
            level = HallucinationLevel.HIGH

        return HallucinationReport(text, level, facts, unsupported, avg_confidence)

    def get_stats(self, report: HallucinationReport) -> Dict[str, Any]:
        return {
            "claims_checked": len(report.facts),
            "verified": len([f for f in report.facts if f.status == FactStatus.VERIFIED]),
            "unsupported": len(report.unsupported_statements),
            "avg_confidence": report.confidence_score,
            "level": report.overall_level.value,
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Anti-Hallucination Engine")
    print("=" * 60)

    engine = AntiHallucinationEngine()
    engine.add_to_kb("Paris", "Paris is the capital of France")
    engine.add_to_kb("Python", "Python is a programming language")
    engine.add_to_kb("Earth", "Earth is the third planet from the Sun")

    texts = [
        "Paris is the capital of France. The Eiffel Tower is located there.",
        "I think Python is a programming language. Maybe it was created by aliens.",
        "The moon is definitely made of cheese. All scientists agree. Water is dry.",
    ]

    for text in texts:
        print(f"\n--- Analyzing: {text[:60]}...")
        report = engine.analyze(text)
        print(f"  Level: {report.overall_level.value}")
        print(f"  Confidence: {report.confidence_score:.2f}")
        print(f"  Unsupported: {len(report.unsupported_statements)}")
        for fact in report.facts:
            print(f"    [{fact.status.value}] {fact.claim_text[:50]}... (conf={fact.confidence:.2f})")

    print("\nAnti-Hallucination test complete.")


if __name__ == "__main__":
    run()
