"""Knowledge Reconciliation Engine — Merging conflicting facts, contradiction detection, truth scoring.

Modul ini menyediakan:
- FactRegistry untuk menyimpan facts dari berbagai sources dengan confidence scores
- ContradictionDetector untuk menemukan facts yang saling bertentangan
- ReconciliationEngine untuk merge / resolve conflicts
- TruthScorer untuk Bayesian-style truth aggregation
- SourceReputation untuk credibility tracking
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class FactStatus(Enum):
    CONFIRMED = auto()
    CONTRADICTED = auto()
    PENDING = auto()
    MERGED = auto()
    REJECTED = auto()


@dataclass
class Fact:
    """A single factual claim."""
    fact_id: str
    subject: str
    predicate: str
    object: str
    source: str
    confidence: float = 0.5  # 0-1
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: FactStatus = FactStatus.PENDING
    merged_from: List[str] = field(default_factory=list)

    def canonical_key(self) -> str:
        return f"{self.subject.lower()}::{self.predicate.lower()}"

    def to_tuple(self) -> Tuple[str, str, str]:
        return (self.subject.lower(), self.predicate.lower(), self.object.lower())


@dataclass
class Contradiction:
    """Detected contradiction between facts."""
    contradiction_id: str
    fact_a: str
    fact_b: str
    reason: str
    severity: float = 1.0  # 0-1
    resolved: bool = False
    resolution: Optional[str] = None


class SourceReputation:
    """Track credibility of sources over time."""

    def __init__(self, default_credibility: float = 0.5):
        self.default = default_credibility
        self._sources: Dict[str, Dict[str, Any]] = {}

    def record(self, source: str, correct: bool) -> None:
        s = self._sources.setdefault(source, {"correct": 0, "incorrect": 0, "total": 0, "credibility": self.default})
        s["total"] += 1
        if correct:
            s["correct"] += 1
        else:
            s["incorrect"] += 1
        s["credibility"] = s["correct"] / max(s["total"], 1)

    def get(self, source: str) -> float:
        return self._sources.get(source, {}).get("credibility", self.default)

    def get_stats(self, source: str) -> Dict[str, Any]:
        return self._sources.get(source, {"correct": 0, "incorrect": 0, "total": 0, "credibility": self.default})


class FactRegistry:
    """Store and index facts from multiple sources."""

    def __init__(self):
        self._facts: Dict[str, Fact] = {}
        self._by_subject: Dict[str, List[str]] = {}
        self._by_predicate: Dict[str, List[str]] = {}
        self._by_source: Dict[str, List[str]] = {}

    def add(self, fact: Fact) -> None:
        self._facts[fact.fact_id] = fact
        self._by_subject.setdefault(fact.subject.lower(), []).append(fact.fact_id)
        self._by_predicate.setdefault(fact.predicate.lower(), []).append(fact.fact_id)
        self._by_source.setdefault(fact.source, []).append(fact.fact_id)

    def get(self, fact_id: str) -> Optional[Fact]:
        return self._facts.get(fact_id)

    def find_by_subject(self, subject: str) -> List[Fact]:
        return [self._facts[fid] for fid in self._by_subject.get(subject.lower(), [])]

    def find_by_predicate(self, predicate: str) -> List[Fact]:
        return [self._facts[fid] for fid in self._by_predicate.get(predicate.lower(), [])]

    def find_by_source(self, source: str) -> List[Fact]:
        return [self._facts[fid] for fid in self._by_source.get(source, [])]

    def get_conflicts(self, predicate: str) -> List[Tuple[Fact, Fact]]:
        """Find facts with same subject+predicate but different objects."""
        facts = self.find_by_predicate(predicate)
        groups: Dict[str, List[Fact]] = {}
        for f in facts:
            groups.setdefault(f.subject.lower(), []).append(f)
        conflicts = []
        for group in groups.values():
            if len(group) > 1:
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        if group[i].object.lower() != group[j].object.lower():
                            conflicts.append((group[i], group[j]))
        return conflicts

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{
                "fact_id": fa.fact_id, "subject": fa.subject, "predicate": fa.predicate,
                "object": fa.object, "source": fa.source, "confidence": fa.confidence,
                "status": fa.status.name, "timestamp": fa.timestamp
            } for fa in self._facts.values()], f, indent=2)


class ContradictionDetector:
    """Detect contradictions between facts."""

    def __init__(self, registry: FactRegistry, reputation: SourceReputation):
        self.registry = registry
        self.reputation = reputation
        self._contradictions: Dict[str, Contradiction] = {}

    def scan_all(self) -> List[Contradiction]:
        """Scan all predicates for conflicts."""
        found = []
        checked = set()
        for pred in self.registry._by_predicate.keys():
            for a, b in self.registry.get_conflicts(pred):
                key = tuple(sorted([a.fact_id, b.fact_id]))
                if key in checked:
                    continue
                checked.add(key)
                severity = self._assess_severity(a, b)
                cid = str(uuid.uuid4())[:12]
                c = Contradiction(cid, a.fact_id, b.fact_id, f"Different objects for {a.subject} {a.predicate}", severity)
                self._contradictions[cid] = c
                a.status = FactStatus.CONTRADICTED
                b.status = FactStatus.CONTRADICTED
                found.append(c)
        return found

    def _assess_severity(self, a: Fact, b: Fact) -> float:
        # High severity if both sources are credible and confident
        ca = self.reputation.get(a.source) * a.confidence
        cb = self.reputation.get(b.source) * b.confidence
        return min(1.0, (ca + cb) / 2 + 0.2)

    def get_contradictions(self) -> List[Contradiction]:
        return list(self._contradictions.values())

    def resolve(self, contradiction_id: str, keep_fact_id: str) -> bool:
        c = self._contradictions.get(contradiction_id)
        if not c:
            return False
        c.resolved = True
        c.resolution = keep_fact_id
        for fid in [c.fact_a, c.fact_b]:
            f = self.registry.get(fid)
            if f:
                f.status = FactStatus.CONFIRMED if fid == keep_fact_id else FactStatus.REJECTED
        return True


class TruthScorer:
    """Aggregate truth value from multiple sources for same claim."""

    def __init__(self, reputation: SourceReputation):
        self.reputation = reputation

    def score(self, facts: List[Fact]) -> float:
        """Bayesian-style aggregation."""
        if not facts:
            return 0.0
        # Weighted average with source credibility
        total_weight = 0.0
        weighted_sum = 0.0
        for f in facts:
            w = self.reputation.get(f.source) * f.confidence
            weighted_sum += w
            total_weight += 1.0  # Count-based, not weight-based for denominator
        # Simple aggregation: weighted average
        return weighted_sum / max(len(facts), 1)

    def consensus(self, facts: List[Fact], threshold: float = 0.7) -> Tuple[bool, float]:
        """Check if facts agree on same object."""
        if not facts:
            return False, 0.0
        objects: Dict[str, float] = {}
        for f in facts:
            obj = f.object.lower()
            w = self.reputation.get(f.source) * f.confidence
            objects[obj] = objects.get(obj, 0.0) + w
        best_obj = max(objects, key=objects.get)
        best_score = objects[best_obj] / max(sum(objects.values()), 1e-9)
        return best_score >= threshold, best_score


class ReconciliationEngine:
    """Merge facts, resolve conflicts, produce canonical knowledge."""

    def __init__(self, registry: FactRegistry, detector: ContradictionDetector, scorer: TruthScorer):
        self.registry = registry
        self.detector = detector
        self.scorer = scorer
        self._merged: Dict[str, Fact] = {}  # canonical_key -> merged fact

    def reconcile(self, predicate: Optional[str] = None) -> List[Fact]:
        """Reconcile all facts for a predicate (or all)."""
        predicates = [predicate] if predicate else list(self.registry._by_predicate.keys())
        results = []
        for pred in predicates:
            conflicts = self.registry.get_conflicts(pred)
            if not conflicts:
                continue
            # Group by subject
            subjects: Dict[str, List[Fact]] = {}
            for a, b in conflicts:
                subjects.setdefault(a.subject.lower(), []).append(a)
                subjects.setdefault(b.subject.lower(), []).append(b)
            # For each subject, find consensus
            for subj, facts in subjects.items():
                # Deduplicate by object
                by_obj: Dict[str, List[Fact]] = {}
                for f in facts:
                    by_obj.setdefault(f.object.lower(), []).append(f)
                # Pick the object with highest aggregated score
                best_obj = None
                best_score = -1.0
                for obj, group in by_obj.items():
                    score = self.scorer.score(group)
                    if score > best_score:
                        best_score = score
                        best_obj = obj
                if best_obj:
                    merged = Fact(
                        fact_id=str(uuid.uuid4())[:12],
                        subject=subj,
                        predicate=pred,
                        object=best_obj,
                        source="merged",
                        confidence=best_score,
                        status=FactStatus.MERGED,
                        merged_from=[f.fact_id for f in facts]
                    )
                    self._merged[merged.canonical_key()] = merged
                    results.append(merged)
        return results

    def get_merged(self) -> List[Fact]:
        return list(self._merged.values())

    def query(self, subject: str, predicate: str) -> Optional[Fact]:
        key = f"{subject.lower()}::{predicate.lower()}"
        return self._merged.get(key) or self.registry.find_by_subject(subject)[0] if self.registry.find_by_subject(subject) else None


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("KNOWLEDGE RECONCILIATION ENGINE DEMO")
    print("=" * 70)

    # Setup
    reputation = SourceReputation(default_credibility=0.5)
    reputation.record("wikipedia", True)
    reputation.record("wikipedia", True)
    reputation.record("wikipedia", True)
    reputation.record("blog_xyz", False)
    reputation.record("news_cnn", True)
    reputation.record("news_cnn", True)
    reputation.record("news_bbc", True)
    reputation.record("news_bbc", True)
    reputation.record("news_bbc", True)
    print(f"\n[1] Source Reputation")
    for src in ["wikipedia", "news_cnn", "news_bbc", "blog_xyz"]:
        print(f"  {src}: {reputation.get(src):.2f}")

    # Add facts
    registry = FactRegistry()
    facts = [
        Fact("f1", "Paris", "capital_of", "France", "wikipedia", confidence=0.95),
        Fact("f2", "Paris", "capital_of", "France", "news_cnn", confidence=0.90),
        Fact("f3", "Paris", "capital_of", "Italy", "blog_xyz", confidence=0.30),
        Fact("f4", "Tokyo", "capital_of", "Japan", "wikipedia", confidence=0.95),
        Fact("f5", "Tokyo", "capital_of", "Japan", "news_bbc", confidence=0.92),
        Fact("f6", "Python", "created_by", "Guido van Rossum", "wikipedia", confidence=0.95),
        Fact("f7", "Python", "created_by", "James Gosling", "blog_xyz", confidence=0.20),
        Fact("f8", "Python", "created_by", "Guido van Rossum", "news_cnn", confidence=0.88),
    ]
    for f in facts:
        registry.add(f)
    print(f"\n[2] Facts Added: {len(facts)} facts")

    # Detect contradictions
    detector = ContradictionDetector(registry, reputation)
    contradictions = detector.scan_all()
    print(f"\n[3] Contradictions Detected: {len(contradictions)}")
    for c in contradictions:
        fa = registry.get(c.fact_a)
        fb = registry.get(c.fact_b)
        print(f"  {c.contradiction_id}: {fa.subject} {fa.predicate} = '{fa.object}' vs '{fb.object}' (severity={c.severity:.2f})")

    # Truth scoring
    scorer = TruthScorer(reputation)
    print(f"\n[4] Truth Scoring")
    paris_facts = registry.find_by_subject("Paris")
    score = scorer.score(paris_facts)
    consensus_ok, consensus_score = scorer.consensus(paris_facts, threshold=0.7)
    print(f"  Paris facts score: {score:.2f}, consensus: {consensus_ok} ({consensus_score:.2f})")

    python_facts = registry.find_by_subject("Python")
    score = scorer.score(python_facts)
    consensus_ok, consensus_score = scorer.consensus(python_facts, threshold=0.7)
    print(f"  Python facts score: {score:.2f}, consensus: {consensus_ok} ({consensus_score:.2f})")

    # Reconcile
    engine = ReconciliationEngine(registry, detector, scorer)
    merged = engine.reconcile()
    print(f"\n[5] Reconciliation Results: {len(merged)} merged facts")
    for m in merged:
        print(f"  {m.subject} {m.predicate} = '{m.object}' (confidence={m.confidence:.2f}, sources={len(m.merged_from)})")

    # Resolve a contradiction manually
    if contradictions:
        c = contradictions[0]
        detector.resolve(c.contradiction_id, c.fact_a)
        print(f"\n[6] Resolved {c.contradiction_id}: kept {c.fact_a}")
        print(f"  Fact A status: {registry.get(c.fact_a).status.name}")
        print(f"  Fact B status: {registry.get(c.fact_b).status.name}")

    # Stats
    print(f"\n[7] Final Stats")
    print(f"  Total facts: {len(registry._facts)}")
    print(f"  Merged facts: {len(engine._merged)}")
    print(f"  Unresolved contradictions: {sum(1 for c in detector.get_contradictions() if not c.resolved)}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
