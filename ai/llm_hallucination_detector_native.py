#!/usr/bin/env python3
"""
llm_hallucination_detector_native.py
Hallucination Detection Engine for MAGNATRIX-OS

Detects hallucinated content in LLM outputs through:
- Self-consistency checks (multiple simulated generations)
- Entropy-based confidence scoring
- Factual claim extraction and knowledge base verification
- Hallucination severity scoring

Pure stdlib. No external dependencies.
"""

from __future__ import annotations

import re
import random
import math
import statistics
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Set, Tuple, Optional, Any


# ── Enums ───────────────────────────────────────────────────────────────────

class Severity(Enum):
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class ClaimType(Enum):
    FACT = auto()
    DATE = auto()
    NUMBER = auto()
    NAME = auto()
    QUOTE = auto()
    STATISTIC = auto()


class Verdict(Enum):
    VERIFIED = auto()
    UNVERIFIED = auto()
    CONTRADICTED = auto()
    UNKNOWN = auto()


# ── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Claim:
    text: str
    claim_type: ClaimType
    span: Tuple[int, int]


@dataclass(frozen=True, slots=True)
class ClaimVerification:
    claim: Claim
    verdict: Verdict
    confidence: float  # 0.0–1.0
    source: Optional[str]


@dataclass(slots=True)
class ConsistencyResult:
    generations: List[str]
    similarity_matrix: List[List[float]]
    average_agreement: float
    divergence_score: float


@dataclass(slots=True)
class EntropyScore:
    token_entropy: float
    sequence_entropy: float
    normalized_confidence: float  # 0.0–1.0, higher = more confident


@dataclass(slots=True)
class HallucinationReport:
    input_text: str
    output_text: str
    consistency: Optional[ConsistencyResult]
    entropy: Optional[EntropyScore]
    claims: List[ClaimVerification]
    overall_severity: Severity
    overall_score: float  # 0.0–1.0, higher = more hallucinated
    details: Dict[str, Any] = field(default_factory=dict)


# ── Mock Knowledge Base ─────────────────────────────────────────────────────

class MockKnowledgeBase:
    """Simulated knowledge base for claim verification."""

    def __init__(self):
        self._facts: Dict[str, Tuple[Verdict, float, Optional[str]]] = {
            "the earth is flat": (Verdict.CONTRADICTED, 0.99, "geodesy"),
            "water boils at 100 celsius": (Verdict.VERIFIED, 0.97, "physics"),
            "paris is the capital of france": (Verdict.VERIFIED, 0.99, "geography"),
            "elon musk founded tesla": (Verdict.VERIFIED, 0.95, "business"),
            "the moon is made of cheese": (Verdict.CONTRADICTED, 0.98, "astronomy"),
            "shakespeare wrote hamlet": (Verdict.VERIFIED, 0.99, "literature"),
            "barack obama was president": (Verdict.VERIFIED, 0.99, "history"),
            "the great wall of china is visible from space": (Verdict.CONTRADICTED, 0.96, "myth"),
            "humans have 206 bones": (Verdict.VERIFIED, 0.94, "biology"),
            "light travels faster than sound": (Verdict.VERIFIED, 0.99, "physics"),
        }

    def verify(self, claim_text: str) -> Tuple[Verdict, float, Optional[str]]:
        normalized = claim_text.lower().strip().rstrip(".!?")
        if normalized in self._facts:
            return self._facts[normalized]
        # Partial match
        for fact, result in self._facts.items():
            if fact in normalized or normalized in fact:
                return result
        return (Verdict.UNKNOWN, 0.5, None)


# ── Claim Extractor ─────────────────────────────────────────────────────────

class ClaimExtractor:
    """Extracts factual claims from text using simple heuristics."""

    # Patterns for different claim types
    DATE_PATTERNS = [
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{4}\b",  # Years
        r"\bin \d{4}\b",
        r"\bsince \d{4}\b",
    ]

    NUMBER_PATTERNS = [
        r"\b\d+\.?\d*\s*(?:percent|percent|million|billion|trillion|km|miles|kg|tons)\b",
        r"\b\d+\.?\d*%\b",
        r"\bover \d+\.?\d*\b",
        r"\babout \d+\.?\d*\b",
    ]

    NAME_PATTERNS = [
        r"\b[A-Z][a-z]+ (?:was|is|were|are|became|founded|created|discovered|invented)\b",
        r"\b[A-Z][a-z]+ [A-Z][a-z]+ (?:was|is|were|are)\b",
    ]

    QUOTE_PATTERNS = [
        r'"([^"]{10,200})"',
        r"'([^']{10,200})'",
    ]

    STATISTIC_PATTERNS = [
        r"\b(?:according to|research shows|studies indicate|data suggests|survey found)\b[^.]*\.",
        r"\b\d+\.?\d*\s*(?:out of|per|of every)\s*\d+\b",
    ]

    def __init__(self):
        self._compiled_patterns: Dict[ClaimType, List[re.Pattern]] = {}
        for ctype, patterns in [
            (ClaimType.DATE, self.DATE_PATTERNS),
            (ClaimType.NUMBER, self.NUMBER_PATTERNS),
            (ClaimType.NAME, self.NAME_PATTERNS),
            (ClaimType.QUOTE, self.QUOTE_PATTERNS),
            (ClaimType.STATISTIC, self.STATISTIC_PATTERNS),
        ]:
            self._compiled_patterns[ctype] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def extract(self, text: str) -> List[Claim]:
        claims: List[Claim] = []
        seen_spans: Set[Tuple[int, int]] = set()

        # Type-specific extraction
        for ctype, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    span = match.span()
                    if span not in seen_spans:
                        seen_spans.add(span)
                        claim_text = match.group(1) if ctype == ClaimType.QUOTE and match.groups() else match.group(0)
                        claims.append(Claim(text=claim_text, claim_type=ctype, span=span))

        # Generic fact sentences (heuristic: sentences with specific entities/numbers)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            # Look for sentences that assert facts
            if re.search(r"\b(is|are|was|were|has|have|had|does|did|will|would|can|could|must|should)\b", sentence, re.IGNORECASE):
                if re.search(r"\b\d+\b|[A-Z][a-z]+ [A-Z][a-z]+", sentence):
                    span_start = text.find(sentence)
                    if span_start >= 0:
                        span = (span_start, span_start + len(sentence))
                        if span not in seen_spans:
                            seen_spans.add(span)
                            claims.append(Claim(text=sentence, claim_type=ClaimType.FACT, span=span))

        return claims


# ── Self-Consistency Engine ─────────────────────────────────────────────────

class SelfConsistencyEngine:
    """Simulates multiple generations and measures agreement."""

    def __init__(self, num_generations: int = 3, random_seed: Optional[int] = None):
        self.num_generations = num_generations
        if random_seed is not None:
            random.seed(random_seed)

    def _simulate_generation(self, input_text: str, variant: int) -> str:
        """Simulate a slightly different generation based on the input."""
        # In a real system, this would call the LLM multiple times with temperature > 0
        # Here we simulate by adding/removing/changing minor details
        base = input_text
        words = base.split()

        if variant == 0:
            return base

        # Apply perturbations
        modified = words[:]
        num_changes = max(1, len(modified) // 20)

        for _ in range(num_changes):
            if not modified:
                break
            idx = random.randint(0, len(modified) - 1)
            op = random.choice(["drop", "replace", "swap"])
            if op == "drop" and len(modified) > 3:
                modified.pop(idx)
            elif op == "replace":
                synonyms = {
                    "large": ["big", "huge", "vast"],
                    "small": ["tiny", "little", "minute"],
                    "fast": ["quick", "rapid", "swift"],
                    "slow": ["sluggish", "gradual", "leisurely"],
                    "important": ["significant", "crucial", "vital"],
                    "good": ["excellent", "fine", "great"],
                }
                word_lower = modified[idx].lower().rstrip(".,;:!?")
                if word_lower in synonyms:
                    modified[idx] = random.choice(synonyms[word_lower])
            elif op == "swap" and idx < len(modified) - 1:
                modified[idx], modified[idx + 1] = modified[idx + 1], modified[idx]

        return " ".join(modified)

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Compute Jaccard similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        intersection = words1 & words2
        union = words1 | words2
        if not union:
            return 1.0
        return len(intersection) / len(union)

    def _semantic_similarity(self, text1: str, text2: str) -> float:
        """Simple semantic similarity using n-gram overlap."""
        def get_ngrams(text: str, n: int = 2) -> Set[str]:
            words = text.lower().split()
            return set(" ".join(words[i:i + n]) for i in range(len(words) - n + 1))

        ngrams1 = get_ngrams(text1)
        ngrams2 = get_ngrams(text2)
        intersection = ngrams1 & ngrams2
        union = ngrams1 | ngrams2
        if not union:
            return 1.0
        return len(intersection) / len(union)

    def check(self, input_text: str, output_text: str) -> ConsistencyResult:
        generations = [self._simulate_generation(output_text, i) for i in range(self.num_generations)]

        n = len(generations)
        sim_matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i == j:
                    sim_matrix[i][j] = 1.0
                else:
                    jaccard = self._jaccard_similarity(generations[i], generations[j])
                    semantic = self._semantic_similarity(generations[i], generations[j])
                    sim_matrix[i][j] = (jaccard + semantic) / 2.0

        # Average agreement (mean of upper triangle)
        agreements = []
        for i in range(n):
            for j in range(i + 1, n):
                agreements.append(sim_matrix[i][j])

        avg_agreement = statistics.mean(agreements) if agreements else 1.0
        divergence = 1.0 - avg_agreement

        return ConsistencyResult(
            generations=generations,
            similarity_matrix=sim_matrix,
            average_agreement=avg_agreement,
            divergence_score=divergence,
        )


# ── Entropy Scorer ────────────────────────────────────────────────────────────

class EntropyScorer:
    """Simulates entropy-based confidence scoring on token distributions."""

    def __init__(self, random_seed: Optional[int] = None):
        if random_seed is not None:
            random.seed(random_seed)

    def score(self, text: str) -> EntropyScore:
        """
        Simulate entropy scoring. In a real system this would use actual
        token log-probabilities from the model. Here we use heuristics.
        """
        words = text.split()
        if not words:
            return EntropyScore(token_entropy=0.0, sequence_entropy=0.0, normalized_confidence=1.0)

        # Heuristic: specific numbers and named entities reduce entropy
        # Generic/vague language increases entropy (hallucination risk)
        vague_terms = ["some", "many", "several", "various", "numerous", "a lot",
                       "often", "sometimes", "frequently", "rarely", "probably",
                       "maybe", "perhaps", "likely", "possibly", "generally",
                       "usually", "typically", "commonly", "widely"]

        specific_patterns = [
            r"\b\d{4}\b",  # Years
            r"\b\d+\.?\d*%\b",  # Percentages
            r"\b\d+\.?\d*\s*(?:million|billion|trillion)\b",
            r"\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b",  # Full names
        ]

        vague_count = sum(1 for w in words if w.lower().rstrip(",.:;!?") in vague_terms)
        specific_count = sum(1 for p in specific_patterns for _ in re.finditer(p, text))

        # Token entropy: higher when vague
        token_entropy = 0.3 + (vague_count / max(len(words), 1)) * 2.0 - (specific_count / max(len(words), 1)) * 1.5
        token_entropy = max(0.0, min(3.0, token_entropy))

        # Sequence entropy: based on sentence length variance
        sentences = re.split(r'[.!?]+', text)
        sent_lengths = [len(s.split()) for s in sentences if s.strip()]
        if len(sent_lengths) > 1:
            try:
                seq_entropy = statistics.stdev(sent_lengths) / statistics.mean(sent_lengths)
            except statistics.StatisticsError:
                seq_entropy = 0.0
        else:
            seq_entropy = 0.0

        # Normalized confidence: inverse of entropy
        raw_confidence = 1.0 - (token_entropy / 3.0) * 0.7 - seq_entropy * 0.3
        normalized = max(0.0, min(1.0, raw_confidence))

        return EntropyScore(
            token_entropy=round(token_entropy, 4),
            sequence_entropy=round(seq_entropy, 4),
            normalized_confidence=round(normalized, 4),
        )


# ── Hallucination Detector Engine ───────────────────────────────────────────

class HallucinationDetectorEngine:
    """Orchestrates all hallucination detection components."""

    def __init__(
        self,
        num_consistency_checks: int = 3,
        claim_threshold: float = 0.3,
        consistency_threshold: float = 0.6,
        entropy_threshold: float = 0.5,
        kb: Optional[MockKnowledgeBase] = None,
    ):
        self.claim_extractor = ClaimExtractor()
        self.consistency_engine = SelfConsistencyEngine(num_generations=num_consistency_checks)
        self.entropy_scorer = EntropyScorer()
        self.kb = kb or MockKnowledgeBase()
        self.claim_threshold = claim_threshold
        self.consistency_threshold = consistency_threshold
        self.entropy_threshold = entropy_threshold

    def _score_claims(self, claims: List[ClaimVerification]) -> float:
        if not claims:
            return 0.0

        scores = []
        for cv in claims:
            if cv.verdict == Verdict.CONTRADICTED:
                scores.append(1.0)
            elif cv.verdict == Verdict.UNKNOWN:
                scores.append(0.5 * (1.0 - cv.confidence))
            elif cv.verdict == Verdict.UNVERIFIED:
                scores.append(0.3 * (1.0 - cv.confidence))
            else:  # VERIFIED
                scores.append(0.0)

        return statistics.mean(scores) if scores else 0.0

    def _compute_severity(self, overall_score: float) -> Severity:
        if overall_score < 0.15:
            return Severity.NONE
        elif overall_score < 0.35:
            return Severity.LOW
        elif overall_score < 0.6:
            return Severity.MEDIUM
        elif overall_score < 0.8:
            return Severity.HIGH
        else:
            return Severity.CRITICAL

    def detect(self, input_text: str, output_text: str) -> HallucinationReport:
        # 1. Consistency check
        consistency = self.consistency_engine.check(input_text, output_text)

        # 2. Entropy scoring
        entropy = self.entropy_scorer.score(output_text)

        # 3. Claim extraction and verification
        claims = self.claim_extractor.extract(output_text)
        claim_results: List[ClaimVerification] = []
        for claim in claims:
            verdict, confidence, source = self.kb.verify(claim.text)
            claim_results.append(ClaimVerification(
                claim=claim,
                verdict=verdict,
                confidence=confidence,
                source=source,
            ))

        # 4. Compute overall score
        claim_score = self._score_claims(claim_results)
        consistency_penalty = max(0.0, consistency.divergence_score - 0.2) * 1.5
        entropy_penalty = max(0.0, self.entropy_threshold - entropy.normalized_confidence)

        overall_score = min(1.0, claim_score * 0.5 + consistency_penalty * 0.25 + entropy_penalty * 0.25)
        overall_score = round(overall_score, 4)

        severity = self._compute_severity(overall_score)

        details = {
            "num_claims_extracted": len(claims),
            "num_contradictions": sum(1 for c in claim_results if c.verdict == Verdict.CONTRADICTED),
            "num_unknown": sum(1 for c in claim_results if c.verdict == Verdict.UNKNOWN),
            "num_verified": sum(1 for c in claim_results if c.verdict == Verdict.VERIFIED),
            "consistency_divergence": round(consistency.divergence_score, 4),
            "entropy_confidence": entropy.normalized_confidence,
        }

        return HallucinationReport(
            input_text=input_text,
            output_text=output_text,
            consistency=consistency,
            entropy=entropy,
            claims=claim_results,
            overall_severity=severity,
            overall_score=overall_score,
            details=details,
        )


# ── Demo ────────────────────────────────────────────────────────────────────

def run_demo() -> None:
    print("=" * 70)
    print("HALLUCINATION DETECTION ENGINE — MAGNATRIX-OS")
    print("=" * 70)

    engine = HallucinationDetectorEngine(num_consistency_checks=3)

    test_cases = [
        {
            "input": "What is the capital of France?",
            "output": "Paris is the capital of France. It has been the capital since 987.",
            "expected": "clean (factual)",
        },
        {
            "input": "Tell me about the Moon.",
            "output": "The Moon is Earth's only natural satellite. It is made of cheese and was first visited by humans in 1969.",
            "expected": "hallucinated (cheese)",
        },
        {
            "input": "Who wrote Hamlet?",
            "output": "William Shakespeare wrote Hamlet around 1599. Some scholars believe Christopher Marlowe co-wrote it.",
            "expected": "mixed (uncertain co-authorship)",
        },
        {
            "input": "What causes lightning?",
            "output": "Lightning is caused by the rapid discharge of electricity between clouds or between a cloud and the ground. It travels faster than sound, which is why you see it before hearing thunder.",
            "expected": "clean (factual)",
        },
        {
            "input": "How many bones are in the human body?",
            "output": "Humans have about 206 bones in their adult body. Babies are born with approximately 270 bones, which later fuse together.",
            "expected": "clean (factual)",
        },
        {
            "input": "Is the Great Wall visible from space?",
            "output": "Yes, the Great Wall of China is easily visible from the Moon with the naked eye. It is the only man-made structure visible from space.",
            "expected": "hallucinated (myth)",
        },
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'─' * 70}")
        print(f"Test {i}: {case['expected']}")
        print(f"Input:  {case['input']}")
        print(f"Output: {case['output'][:80]}{'...' if len(case['output']) > 80 else ''}")
        print("─" * 70)

        report = engine.detect(case["input"], case["output"])

        print(f"Overall Score:     {report.overall_score:.4f}")
        print(f"Severity:          {report.overall_severity.name}")
        print(f"Consistency Divergence: {report.consistency.divergence_score:.4f}")
        print(f"Entropy Confidence:     {report.entropy.normalized_confidence:.4f}")
        print(f"Claims Found:      {report.details['num_claims_extracted']}")
        print(f"  Verified:        {report.details['num_verified']}")
        print(f"  Unknown:         {report.details['num_unknown']}")
        print(f"  Contradicted:    {report.details['num_contradictions']}")

        if report.claims:
            print("\n  Claim Details:")
            for cv in report.claims:
                flag = "✓" if cv.verdict == Verdict.VERIFIED else "✗" if cv.verdict == Verdict.CONTRADICTED else "?"
                print(f"    [{flag}] ({cv.claim.claim_type.name}) {cv.claim.text[:60]}...")
                print(f"        → Verdict: {cv.verdict.name}, Confidence: {cv.confidence:.2f}")

    print(f"\n{'=' * 70}")
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
