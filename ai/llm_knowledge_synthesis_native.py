"""Knowledge Synthesis — Cross-document synthesis, contradiction detection, consensus building, source merging.

Modul ini menyediakan:
- DocumentSynthesizer untuk merging multiple documents
- ContradictionDetector untuk detect conflicting claims
- ConsensusBuilder untuk find agreement across sources
- SourceMerger untuk merge dan deduplicate sources
- KnowledgeFusion untuk fusion knowledge graph dari multiple docs

Arsitektur: Documents → Parse → Detect → Resolve → Merge → Synthesize
"""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ConflictType(Enum):
    DIRECT = auto()
    IMPLIED = auto()
    TEMPORAL = auto()
    SCOPE = auto()


class ResolutionStrategy(Enum):
    MAJORITY = auto()
    AUTHORITY = auto()
    RECENCY = auto()
    CONSERVATIVE = auto()


@dataclass
class Claim:
    """Single claim from a document."""
    claim_id: str
    statement: str
    source: str
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_claims: List[str] = field(default_factory=list)

    def hash(self) -> str:
        return hashlib.sha256(self.statement.encode()).hexdigest()[:16]


@dataclass
class Conflict:
    """Detected conflict between claims."""
    conflict_id: str
    claim_a: Claim
    claim_b: Claim
    conflict_type: ConflictType
    description: str
    severity: float = 0.0


@dataclass
class SynthesisResult:
    """Result of knowledge synthesis."""
    result_id: str
    synthesized_text: str
    sources_used: List[str]
    conflicts_resolved: List[Conflict]
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentSynthesizer:
    """Synthesize information from multiple documents."""

    def __init__(self):
        self._documents: Dict[str, str] = {}
        self._claims: Dict[str, Claim] = {}

    def add_document(self, doc_id: str, content: str) -> None:
        self._documents[doc_id] = content
        # Extract simple claims (sentences)
        sentences = [s.strip() for s in content.split(".") if s.strip()]
        for i, sent in enumerate(sentences):
            claim = Claim(
                claim_id=f"{doc_id}-claim-{i}",
                statement=sent,
                source=doc_id
            )
            self._claims[claim.claim_id] = claim

    def synthesize(self, query: str, strategy: ResolutionStrategy = ResolutionStrategy.MAJORITY) -> SynthesisResult:
        relevant = self._find_relevant(query)
        if not relevant:
            return SynthesisResult(
                result_id=str(uuid.uuid4())[:12],
                synthesized_text="No relevant information found.",
                sources_used=[],
                conflicts_resolved=[]
            )

        # Detect conflicts
        conflicts = self._detect_conflicts(relevant)
        resolved = self._resolve_conflicts(conflicts, strategy)

        # Build synthesis
        parts = []
        sources = set()
        for claim in resolved:
            parts.append(claim.statement)
            sources.add(claim.source)

        text = ". ".join(parts) + "."
        avg_conf = sum(c.confidence for c in resolved) / max(len(resolved), 1)

        return SynthesisResult(
            result_id=str(uuid.uuid4())[:12],
            synthesized_text=text,
            sources_used=list(sources),
            conflicts_resolved=conflicts,
            confidence=round(avg_conf, 4)
        )

    def _find_relevant(self, query: str) -> List[Claim]:
        query_words = set(query.lower().split())
        relevant = []
        for claim in self._claims.values():
            claim_words = set(claim.statement.lower().split())
            overlap = len(query_words & claim_words)
            if overlap > 0:
                relevant.append((overlap, claim))
        relevant.sort(reverse=True, key=lambda x: x[0])
        return [c for _, c in relevant]

    def _detect_conflicts(self, claims: List[Claim]) -> List[Conflict]:
        conflicts = []
        for i, a in enumerate(claims):
            for b in claims[i+1:]:
                if a.source == b.source:
                    continue
                # Simple conflict detection: negation keywords
                a_neg = any(w in a.statement.lower() for w in ["not", "no", "never", "false"])
                b_neg = any(w in b.statement.lower() for w in ["not", "no", "never", "false"])
                if a_neg != b_neg and len(set(a.statement.lower().split()) & set(b.statement.lower().split())) > 3:
                    conflicts.append(Conflict(
                        conflict_id=str(uuid.uuid4())[:12],
                        claim_a=a,
                        claim_b=b,
                        conflict_type=ConflictType.DIRECT,
                        description=f"Contradictory claims about similar subject",
                        severity=0.8
                    ))
        return conflicts

    def _resolve_conflicts(self, conflicts: List[Conflict], strategy: ResolutionStrategy) -> List[Claim]:
        # Simple resolution: keep claims from preferred sources
        all_claims = list(self._claims.values())
        if strategy == ResolutionStrategy.MAJORITY:
            # Count occurrences of similar claims
            claim_groups = {}
            for c in all_claims:
                key = c.hash()[:8]
                claim_groups.setdefault(key, []).append(c)
            # Keep majority
            resolved = []
            for group in claim_groups.values():
                best = max(group, key=lambda x: x.confidence)
                resolved.append(best)
            return resolved
        elif strategy == ResolutionStrategy.RECENCY:
            return sorted(all_claims, key=lambda x: x.timestamp, reverse=True)[:len(all_claims) // 2 + 1]
        else:
            return all_claims

    def get_document_count(self) -> int:
        return len(self._documents)

    def get_claim_count(self) -> int:
        return len(self._claims)


class ContradictionDetector:
    """Detect contradictions in text or between sources."""

    def __init__(self):
        self._negation_words = ["not", "no", "never", "false", "incorrect", "wrong", "impossible"]
        self._contradiction_patterns: List[Tuple[str, str]] = [
            ("is", "is not"),
            ("can", "cannot"),
            ("will", "will not"),
            ("always", "never"),
            ("all", "none"),
        ]

    def detect(self, claims: List[Claim]) -> List[Conflict]:
        conflicts = []
        for i, a in enumerate(claims):
            for b in claims[i+1:]:
                if a.source == b.source:
                    continue
                if self._is_contradictory(a.statement, b.statement):
                    conflicts.append(Conflict(
                        conflict_id=str(uuid.uuid4())[:12],
                        claim_a=a,
                        claim_b=b,
                        conflict_type=ConflictType.DIRECT,
                        description="Direct contradiction detected",
                        severity=0.9
                    ))
        return conflicts

    def _is_contradictory(self, a: str, b: str) -> bool:
        a_lower = a.lower()
        b_lower = b.lower()
        # Check negation patterns
        for pos, neg in self._contradiction_patterns:
            if pos in a_lower and neg in b_lower:
                if len(set(a_lower.split()) & set(b_lower.split())) > 2:
                    return True
            if neg in a_lower and pos in b_lower:
                if len(set(a_lower.split()) & set(b_lower.split())) > 2:
                    return True
        return False

    def detect_internal(self, text: str) -> List[Tuple[str, str, str]]:
        """Detect contradictions within a single text."""
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        contradictions = []
        for i, s1 in enumerate(sentences):
            for s2 in sentences[i+1:]:
                if self._is_contradictory(s1, s2):
                    contradictions.append((s1, s2, "Internal contradiction"))
        return contradictions


class ConsensusBuilder:
    """Find consensus among multiple sources."""

    def __init__(self, agreement_threshold: float = 0.6):
        self.agreement_threshold = agreement_threshold

    def build(self, claims: List[Claim]) -> Dict[str, Any]:
        # Group by topic similarity
        groups = self._group_by_similarity(claims)
        consensus = []
        disagreements = []
        for group in groups:
            if len(group) < 2:
                continue
            agreement = self._calculate_agreement(group)
            if agreement >= self.agreement_threshold:
                consensus.append({
                    "topic": group[0].statement[:50],
                    "agreement": agreement,
                    "sources": list(set(c.source for c in group)),
                    "claims": len(group)
                })
            else:
                disagreements.append({
                    "topic": group[0].statement[:50],
                    "agreement": agreement,
                    "sources": list(set(c.source for c in group)),
                })
        return {
            "consensus_items": consensus,
            "disagreements": disagreements,
            "consensus_rate": len(consensus) / max(len(consensus) + len(disagreements), 1)
        }

    def _group_by_similarity(self, claims: List[Claim]) -> List[List[Claim]]:
        groups = []
        used = set()
        for claim in claims:
            if claim.claim_id in used:
                continue
            group = [claim]
            used.add(claim.claim_id)
            for other in claims:
                if other.claim_id in used:
                    continue
                if self._similarity(claim, other) > 0.5:
                    group.append(other)
                    used.add(other.claim_id)
            groups.append(group)
        return groups

    def _similarity(self, a: Claim, b: Claim) -> float:
        a_words = set(a.statement.lower().split())
        b_words = set(b.statement.lower().split())
        intersection = len(a_words & b_words)
        union = len(a_words | b_words)
        return intersection / union if union > 0 else 0.0

    def _calculate_agreement(self, group: List[Claim]) -> float:
        if len(group) < 2:
            return 1.0
        # Check if all have same polarity (negation)
        negations = [any(w in c.statement.lower() for w in ["not", "no", "never"]) for c in group]
        if all(n == negations[0] for n in negations):
            return 1.0
        return sum(1 for n in negations if n == negations[0]) / len(negations)


class SourceMerger:
    """Merge and deduplicate sources."""

    def __init__(self):
        self._sources: Dict[str, Dict[str, Any]] = {}

    def add_source(self, source_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._sources[source_id] = {
            "content": content,
            "metadata": metadata or {},
            "hash": hashlib.sha256(content.encode()).hexdigest()[:16]
        }

    def merge(self) -> Tuple[str, Dict[str, Any]]:
        # Deduplicate by hash
        unique = {}
        for sid, data in self._sources.items():
            h = data["hash"]
            if h not in unique:
                unique[h] = data

        parts = []
        for data in unique.values():
            parts.append(data["content"])

        merged = "\n\n".join(parts)
        stats = {
            "total_sources": len(self._sources),
            "unique_sources": len(unique),
            "duplicates": len(self._sources) - len(unique),
            "merged_length": len(merged)
        }
        return merged, stats

    def get_source_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._sources),
            "hashes": [d["hash"] for d in self._sources.values()]
        }


class KnowledgeFusion:
    """Fuse knowledge from multiple documents into unified representation."""

    def __init__(self):
        self.synthesizer = DocumentSynthesizer()
        self.detector = ContradictionDetector()
        self.consensus = ConsensusBuilder()
        self.merger = SourceMerger()

    def fuse(self, documents: Dict[str, str], query: str = "",
             strategy: ResolutionStrategy = ResolutionStrategy.MAJORITY) -> Dict[str, Any]:
        # Add documents
        for doc_id, content in documents.items():
            self.synthesizer.add_document(doc_id, content)
            self.merger.add_source(doc_id, content)

        # Synthesize
        synthesis = self.synthesizer.synthesize(query, strategy)

        # Detect conflicts
        all_claims = list(self.synthesizer._claims.values())
        conflicts = self.detector.detect(all_claims)

        # Build consensus
        consensus = self.consensus.build(all_claims)

        # Merge sources
        merged, merge_stats = self.merger.merge()

        return {
            "synthesis": {
                "text": synthesis.synthesized_text[:200] + "..." if len(synthesis.synthesized_text) > 200 else synthesis.synthesized_text,
                "confidence": synthesis.confidence,
                "sources": synthesis.sources_used
            },
            "conflicts": {
                "count": len(conflicts),
                "details": [
                    {"a": c.claim_a.statement[:50], "b": c.claim_b.statement[:50], "type": c.conflict_type.name}
                    for c in conflicts[:5]
                ]
            },
            "consensus": consensus,
            "merge_stats": merge_stats,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "documents": self.synthesizer.get_document_count(),
            "claims": self.synthesizer.get_claim_count(),
            "sources": len(self.merger._sources),
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("KNOWLEDGE SYNTHESIS DEMO")
    print("=" * 70)

    fusion = KnowledgeFusion()

    # 1. Add documents
    print("\n[1] Add Documents")
    docs = {
        "doc1": "Python is a programming language. It is widely used for data science. Python is easy to learn.",
        "doc2": "Python is not just a programming language. It is also a scripting language. Python is very popular.",
        "doc3": "Java is a programming language. Java is used for enterprise applications. Java is statically typed.",
    }
    for doc_id, content in docs.items():
        fusion.synthesizer.add_document(doc_id, content)
        fusion.merger.add_source(doc_id, content)
    print(f"  Documents: {len(docs)}")
    print(f"  Claims: {fusion.synthesizer.get_claim_count()}")

    # 2. Synthesize
    print("\n[2] Synthesize")
    result = fusion.synthesizer.synthesize("programming languages")
    print(f"  Synthesized: {result.synthesized_text[:100]}...")
    print(f"  Confidence: {result.confidence}")
    print(f"  Sources: {result.sources_used}")
    print(f"  Conflicts: {len(result.conflicts_resolved)}")

    # 3. Contradiction detection
    print("\n[3] Contradiction Detection")
    all_claims = list(fusion.synthesizer._claims.values())
    conflicts = fusion.detector.detect(all_claims)
    print(f"  Conflicts found: {len(conflicts)}")
    for c in conflicts[:3]:
        print(f"    [{c.severity}] '{c.claim_a.statement[:40]}...' vs '{c.claim_b.statement[:40]}...'")

    # 4. Internal contradiction
    print("\n[4] Internal Contradiction Detection")
    contradictory_text = "Python is easy to learn. Python is not easy to learn. It is widely used."
    internal = fusion.detector.detect_internal(contradictory_text)
    print(f"  Internal contradictions: {len(internal)}")
    for s1, s2, desc in internal:
        print(f"    '{s1}' vs '{s2}'")

    # 5. Consensus building
    print("\n[5] Consensus Building")
    consensus = fusion.consensus.build(all_claims)
    print(f"  Consensus items: {len(consensus['consensus_items'])}")
    print(f"  Disagreements: {len(consensus['disagreements'])}")
    print(f"  Consensus rate: {consensus['consensus_rate']:.2%}")
    for item in consensus['consensus_items'][:2]:
        print(f"    Topic: {item['topic']}, Agreement: {item['agreement']:.2f}")

    # 6. Source merging
    print("\n[6] Source Merging")
    merged, stats = fusion.merger.merge()
    print(f"  Total sources: {stats['total_sources']}")
    print(f"  Unique sources: {stats['unique_sources']}")
    print(f"  Duplicates removed: {stats['duplicates']}")
    print(f"  Merged length: {stats['merged_length']} chars")

    # 7. Full fusion
    print("\n[7] Full Knowledge Fusion")
    fusion2 = KnowledgeFusion()
    result = fusion2.fuse(docs, "programming languages")
    print(f"  Synthesis text: {result['synthesis']['text'][:80]}...")
    print(f"  Conflicts: {result['conflicts']['count']}")
    print(f"  Consensus rate: {result['consensus']['consensus_rate']:.2%}")

    # 8. Stats
    print("\n[8] Stats")
    print(f"  {fusion.get_stats()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
