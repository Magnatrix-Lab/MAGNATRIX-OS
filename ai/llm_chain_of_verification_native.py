#!/usr/bin/env python3
"""
MAGNATRIX-OS — Chain of Verification Engine
ai/llm_chain_of_verification_native.py

Features:
- Claim extraction from text (identify factual claims)
- Verification chain generation (decompose claims into verifiable sub-claims)
- Evidence scoring (confidence per claim based on supporting evidence)
- Verification chain execution (pass/fail per sub-claim)
- Corrected output generation (rewrite with only verified claims)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("chain_verification")


class ClaimStatus(enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    REFUTED = "refuted"


class EvidenceType(enum.Enum):
    INTERNAL = "internal"       # from knowledge base
    EXTERNAL = "external"       # from search/web
    LOGICAL = "logical"         # from logical deduction
    STATISTICAL = "statistical"  # from data


@dataclass
class Claim:
    id: str
    text: str
    confidence: float = 0.0
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    evidence: List[Evidence] = field(default_factory=list)
    sub_claims: List["Claim"] = field(default_factory=list)
    parent_id: Optional[str] = None

    @property
    def is_verified(self) -> bool:
        return self.status == ClaimStatus.VERIFIED


@dataclass
class Evidence:
    source: str
    type: EvidenceType
    confidence: float
    snippet: str


@dataclass
class VerificationResult:
    claim: Claim
    verdict: ClaimStatus
    confidence: float
    reasoning: str


class ClaimExtractor:
    """Extract factual claims from text."""

    PATTERNS = [
        r"([A-Z][^.]*?(?:is|are|was|were|has|have|had|does|do|did|will|would|can|could|should)[^.]*\\.)",
        r"([A-Z][^.]*?(?:contains|includes|consists|comprises|represents)[^.]*\\.)",
        r"([A-Z][^.]*?\\d+[^.]*\\.)",  # sentences with numbers
    ]

    def extract(self, text: str) -> List[Claim]:
        claims = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for i, sent in enumerate(sentences):
            if len(sent) > 20 and self._is_factual(sent):
                claims.append(Claim(id=f"C{i}", text=sent.strip()))
        return claims

    def _is_factual(self, sentence: str) -> bool:
        factual_keywords = ["is", "are", "was", "were", "has", "have", "had", "contains", "includes", "%", "$", "°"]
        return any(kw in sentence.lower() for kw in factual_keywords)


class VerificationChain:
    """Build and execute verification chains."""

    def __init__(self, knowledge_base: Optional[Dict[str, str]] = None):
        self._kb = knowledge_base or {}

    def decompose(self, claim: Claim) -> List[Claim]:
        """Decompose a claim into sub-claims."""
        sub_claims = []
        # Simple decomposition: split by conjunctions
        parts = re.split(r'\s+(?:and|but|also|furthermore|moreover)\s+', claim.text)
        for i, part in enumerate(parts):
            if part.strip() and part != claim.text:
                sub = Claim(id=f"{claim.id}-S{i}", text=part.strip(), parent_id=claim.id)
                sub_claims.append(sub)
        if not sub_claims:
            sub_claims = [claim]
        return sub_claims

    def verify(self, claim: Claim) -> VerificationResult:
        """Verify a claim against knowledge base."""
        evidence = self._gather_evidence(claim)
        total_confidence = sum(e.confidence for e in evidence) / max(len(evidence), 1)

        if total_confidence >= 0.8:
            verdict = ClaimStatus.VERIFIED
        elif total_confidence >= 0.5:
            verdict = ClaimStatus.PARTIALLY_VERIFIED
        elif total_confidence >= 0.2:
            verdict = ClaimStatus.UNVERIFIED
        else:
            verdict = ClaimStatus.REFUTED

        claim.evidence = evidence
        claim.status = verdict
        claim.confidence = total_confidence

        return VerificationResult(
            claim=claim,
            verdict=verdict,
            confidence=total_confidence,
            reasoning=f"Based on {len(evidence)} evidence sources with avg confidence {total_confidence:.2f}",
        )

    def _gather_evidence(self, claim: Claim) -> List[Evidence]:
        evidence = []
        claim_lower = claim.text.lower()
        # Check knowledge base
        for key, value in self._kb.items():
            if key.lower() in claim_lower or any(word in claim_lower for word in key.lower().split()):
                evidence.append(Evidence(
                    source=f"kb:{key}", type=EvidenceType.INTERNAL,
                    confidence=0.9, snippet=value[:100],
                ))
        # Simulate external search evidence
        if any(word in claim_lower for word in ["population", "capital", "gdp", "area", "year"]):
            evidence.append(Evidence(
                source="external_search", type=EvidenceType.EXTERNAL,
                confidence=0.75, snippet=f"Simulated search result for: {claim.text[:50]}...",
            ))
        # Logical evidence
        if "all" in claim_lower or "every" in claim_lower or "none" in claim_lower:
            evidence.append(Evidence(
                source="logical_analysis", type=EvidenceType.LOGICAL,
                confidence=0.6, snippet="Universal quantifier detected - requires strong evidence",
            ))
        return evidence


class ChainOfVerificationEngine:
    """End-to-end chain of verification."""

    def __init__(self, knowledge_base: Optional[Dict[str, str]] = None):
        self.extractor = ClaimExtractor()
        self.chain = VerificationChain(knowledge_base)
        self._results: List[VerificationResult] = []

    def verify_text(self, text: str) -> Dict[str, Any]:
        claims = self.extractor.extract(text)
        verified = []
        for claim in claims:
            sub_claims = self.chain.decompose(claim)
            claim.sub_claims = sub_claims
            sub_results = []
            all_verified = True
            for sub in sub_claims:
                result = self.chain.verify(sub)
                sub_results.append(result)
                self._results.append(result)
                if result.verdict != ClaimStatus.VERIFIED:
                    all_verified = False
            if all_verified and len(sub_claims) > 0:
                claim.status = ClaimStatus.VERIFIED
                claim.confidence = min(r.confidence for r in sub_results)
            else:
                claim.status = ClaimStatus.PARTIALLY_VERIFIED if sub_results else ClaimStatus.UNVERIFIED
            verified.append({
                "claim": claim.text,
                "status": claim.status.value,
                "confidence": claim.confidence,
                "sub_results": [{"text": r.claim.text, "verdict": r.verdict.value, "confidence": r.confidence} for r in sub_results],
            })
        return {
            "original_text": text,
            "claims_found": len(claims),
            "verified_results": verified,
            "overall_verified": all(c["status"] == "verified" for c in verified) if verified else False,
        }

    def generate_corrected(self, text: str) -> str:
        result = self.verify_text(text)
        verified_claims = [r for r in result["verified_results"] if r["status"] == "verified"]
        if not verified_claims:
            return "[WARNING: No claims could be fully verified]"
        return " ".join(c["claim"] for c in verified_claims)

    def get_results(self) -> List[VerificationResult]:
        return list(self._results)


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Chain of Verification Engine")
    print("ai/llm_chain_of_verification_native.py")
    print("=" * 60)

    kb = {
        "Paris": "Paris is the capital of France with a population of 2.1 million.",
        "France": "France is a country in Western Europe with a population of 67 million.",
        "Python": "Python is a programming language created by Guido van Rossum in 1991.",
        "Earth": "Earth is the third planet from the Sun with a population of 8 billion.",
    }

    engine = ChainOfVerificationEngine(knowledge_base=kb)

    # 1. Simple claim extraction
    print("")
    print("[1] Claim Extraction")
    text = "Paris is the capital of France. The population of France is 67 million. Python is a language."
    result = engine.verify_text(text)
    print(f"  Claims found: {result['claims_found']}")
    for r in result["verified_results"]:
        print(f"  [{r['status']}] {r['claim'][:60]}... (confidence={r['confidence']:.2f})")

    # 2. Complex claim with decomposition
    print("")
    print("[2] Complex Claim Decomposition")
    text2 = "Paris is the capital of France and the population of France is 67 million."
    result2 = engine.verify_text(text2)
    for r in result2["verified_results"]:
        print(f"  Claim: {r['claim'][:50]}...")
        for sr in r.get("sub_results", []):
            print(f"    Sub: [{sr['verdict']}] {sr['text'][:40]}... (conf={sr['confidence']:.2f})")

    # 3. Corrected output
    print("")
    print("[3] Corrected Output Generation")
    text3 = "Paris is the capital of France. Python was created in 1985. Earth has 1 billion people."
    corrected = engine.generate_corrected(text3)
    print(f"  Original: {text3}")
    print(f"  Corrected: {corrected}")

    # 4. Unverifiable claim
    print("")
    print("[4] Unverifiable Claim")
    text4 = "All aliens speak French and the moon is made of cheese."
    result4 = engine.verify_text(text4)
    for r in result4["verified_results"]:
        print(f"  [{r['status']}] {r['claim'][:50]}...")

    print("")
    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
