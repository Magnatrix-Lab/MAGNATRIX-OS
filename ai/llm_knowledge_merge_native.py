"""Knowledge Consolidation — Merge knowledge bases, deduplication, conflict resolution.

Modul ini menyediakan:
- KnowledgeSource: represent a source of knowledge
- KnowledgeMerger: merge multiple sources with conflict resolution
- DeduplicationEngine: find and merge duplicate facts
- ConflictResolver: resolve conflicting information
- KnowledgeConsolidator: end-to-end knowledge consolidation pipeline
"""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum, auto


class ConflictResolution(Enum):
    KEEP_FIRST = auto()
    KEEP_LAST = auto()
    KEEP_HIGHEST_CONFIDENCE = auto()
    KEEP_MOST_RECENT = auto()
    KEEP_ALL = auto()
    MERGE = auto()
    MANUAL = auto()


@dataclass
class KnowledgeFact:
    """Single knowledge fact."""
    fact_id: str
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.sha256(f"{self.subject}:{self.predicate}:{self.object}".encode()).hexdigest()[:16]

    def to_tuple(self) -> Tuple[str, str, str]:
        return (self.subject, self.predicate, self.object)


@dataclass
class KnowledgeSource:
    """Source of knowledge with provenance."""
    source_id: str
    name: str
    facts: List[KnowledgeFact] = field(default_factory=list)
    reliability: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_fact(self, fact: KnowledgeFact) -> None:
        fact.source = self.source_id
        self.facts.append(fact)

    def get_facts_by_subject(self, subject: str) -> List[KnowledgeFact]:
        return [f for f in self.facts if f.subject == subject]


@dataclass
class Conflict:
    """Detected conflict between facts."""
    conflict_id: str
    fact_a: KnowledgeFact
    fact_b: KnowledgeFact
    conflict_type: str = "value"  # value, temporal, source
    severity: float = 1.0


class DeduplicationEngine:
    """Find and merge duplicate facts."""

    def __init__(self, similarity_threshold: float = 0.9):
        self.threshold = similarity_threshold
        self._duplicates_found = 0
        self._merged = 0

    def find_duplicates(self, facts: List[KnowledgeFact]) -> List[Tuple[KnowledgeFact, KnowledgeFact]]:
        """Find pairs of duplicate facts."""
        duplicates = []
        seen = {}
        for fact in facts:
            key = (fact.subject, fact.predicate)
            if key in seen:
                other = seen[key]
                if fact.object == other.object:
                    duplicates.append((other, fact))
                    self._duplicates_found += 1
            else:
                seen[key] = fact
        return duplicates

    def merge_duplicates(self, facts: List[KnowledgeFact]) -> List[KnowledgeFact]:
        """Merge duplicates, keeping highest confidence."""
        merged = {}
        for fact in facts:
            key = (fact.subject, fact.predicate, fact.object)
            if key in merged:
                existing = merged[key]
                if fact.confidence > existing.confidence:
                    merged[key] = fact
            else:
                merged[key] = fact
        self._merged = len(facts) - len(merged)
        return list(merged.values())

    def get_stats(self) -> Dict[str, int]:
        return {"duplicates_found": self._duplicates_found, "merged": self._merged}


class ConflictResolver:
    """Resolve conflicting information."""

    def __init__(self, strategy: ConflictResolution = ConflictResolution.KEEP_HIGHEST_CONFIDENCE):
        self.strategy = strategy
        self._conflicts: List[Conflict] = []
        self._resolved = 0

    def detect_conflicts(self, facts: List[KnowledgeFact]) -> List[Conflict]:
        """Detect conflicts: same subject+predicate, different object."""
        conflicts = []
        by_key: Dict[Tuple[str, str], List[KnowledgeFact]] = {}
        for fact in facts:
            key = (fact.subject, fact.predicate)
            by_key.setdefault(key, []).append(fact)
        for key, group in by_key.items():
            objects = set(f.object for f in group)
            if len(objects) > 1:
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        conflict = Conflict(
                            conflict_id=str(uuid.uuid4())[:12],
                            fact_a=group[i],
                            fact_b=group[j],
                            severity=abs(group[i].confidence - group[j].confidence)
                        )
                        conflicts.append(conflict)
                        self._conflicts.append(conflict)
        return conflicts

    def resolve(self, conflicts: List[Conflict]) -> List[KnowledgeFact]:
        """Resolve conflicts using strategy."""
        resolved = []
        for conflict in conflicts:
            winner = self._pick_winner(conflict)
            if winner:
                resolved.append(winner)
                self._resolved += 1
        return resolved

    def _pick_winner(self, conflict: Conflict) -> Optional[KnowledgeFact]:
        if self.strategy == ConflictResolution.KEEP_HIGHEST_CONFIDENCE:
            return conflict.fact_a if conflict.fact_a.confidence >= conflict.fact_b.confidence else conflict.fact_b
        elif self.strategy == ConflictResolution.KEEP_MOST_RECENT:
            return conflict.fact_a if conflict.fact_a.timestamp >= conflict.fact_b.timestamp else conflict.fact_b
        elif self.strategy == ConflictResolution.KEEP_FIRST:
            return conflict.fact_a
        elif self.strategy == ConflictResolution.KEEP_LAST:
            return conflict.fact_b
        elif self.strategy == ConflictResolution.KEEP_ALL:
            return None
        return conflict.fact_a

    def get_stats(self) -> Dict[str, int]:
        return {"conflicts_detected": len(self._conflicts), "resolved": self._resolved}


class KnowledgeMerger:
    """Merge multiple knowledge sources."""

    def __init__(self, dedup: Optional[DeduplicationEngine] = None,
                 resolver: Optional[ConflictResolver] = None):
        self.dedup = dedup or DeduplicationEngine()
        self.resolver = resolver or ConflictResolver()
        self._merged_facts: List[KnowledgeFact] = []
        self._source_stats: Dict[str, int] = {}

    def merge(self, sources: List[KnowledgeSource]) -> List[KnowledgeFact]:
        """Merge all sources into single knowledge base."""
        all_facts = []
        for source in sources:
            all_facts.extend(source.facts)
            self._source_stats[source.source_id] = len(source.facts)
        # Step 1: Deduplicate
        deduped = self.dedup.merge_duplicates(all_facts)
        # Step 2: Detect conflicts
        conflicts = self.resolver.detect_conflicts(deduped)
        # Step 3: Resolve conflicts
        if conflicts:
            resolved = self.resolver.resolve(conflicts)
            # Remove conflicting facts, add resolved
            conflict_ids = set()
            for c in conflicts:
                conflict_ids.add(c.fact_a.fact_id)
                conflict_ids.add(c.fact_b.fact_id)
            deduped = [f for f in deduped if f.fact_id not in conflict_ids]
            deduped.extend(resolved)
        self._merged_facts = deduped
        return deduped

    def get_stats(self) -> Dict[str, Any]:
        return {
            "sources": len(self._source_stats),
            "source_breakdown": self._source_stats,
            "total_facts": len(self._merged_facts),
            "dedup": self.dedup.get_stats(),
            "conflicts": self.resolver.get_stats()
        }


class KnowledgeConsolidator:
    """End-to-end knowledge consolidation pipeline."""

    def __init__(self):
        self.sources: List[KnowledgeSource] = []
        self.merger = KnowledgeMerger()
        self._consolidated: List[KnowledgeFact] = []
        self._runs: List[Dict[str, Any]] = []

    def add_source(self, source: KnowledgeSource) -> None:
        self.sources.append(source)

    def consolidate(self) -> List[KnowledgeFact]:
        self._consolidated = self.merger.merge(self.sources)
        run_record = {
            "run_id": str(uuid.uuid4())[:12],
            "timestamp": time.time(),
            "sources": len(self.sources),
            "facts_in": sum(len(s.facts) for s in self.sources),
            "facts_out": len(self._consolidated),
            "stats": self.merger.get_stats()
        }
        self._runs.append(run_record)
        return self._consolidated

    def query(self, subject: Optional[str] = None, predicate: Optional[str] = None) -> List[KnowledgeFact]:
        results = self._consolidated
        if subject:
            results = [f for f in results if f.subject == subject]
        if predicate:
            results = [f for f in results if f.predicate == predicate]
        return results

    def get_graph(self) -> Dict[str, List[Dict[str, str]]]:
        """Export as simple graph format."""
        nodes = set()
        edges = []
        for fact in self._consolidated:
            nodes.add(fact.subject)
            nodes.add(fact.object)
            edges.append({
                "source": fact.subject,
                "relation": fact.predicate,
                "target": fact.object,
                "confidence": fact.confidence
            })
        return {"nodes": list(nodes), "edges": edges}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "sources": len(self.sources),
            "consolidated_facts": len(self._consolidated),
            "runs": len(self._runs),
            "last_run": self._runs[-1] if self._runs else None
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "facts": [{"subject": f.subject, "predicate": f.predicate, "object": f.object,
                          "confidence": f.confidence, "source": f.source}
                         for f in self._consolidated],
                "graph": self.get_graph()
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("KNOWLEDGE CONSOLIDATION DEMO")
    print("=" * 70)

    # 1. Create knowledge sources
    print("\n[1] Knowledge Sources")
    source_a = KnowledgeSource("src-a", "Wikipedia", reliability=0.9)
    source_a.add_fact(KnowledgeFact("f1", "Paris", "capital_of", "France", 0.95))
    source_a.add_fact(KnowledgeFact("f2", "Berlin", "capital_of", "Germany", 0.95))
    source_a.add_fact(KnowledgeFact("f3", "Python", "created_by", "Guido van Rossum", 0.9))
    source_a.add_fact(KnowledgeFact("f4", "Python", "first_release", "1991", 0.85))

    source_b = KnowledgeSource("src-b", "GitHub Docs", reliability=0.85)
    source_b.add_fact(KnowledgeFact("f5", "Python", "created_by", "Guido van Rossum", 0.92))
    source_b.add_fact(KnowledgeFact("f6", "Python", "first_release", "1994", 0.7))
    source_b.add_fact(KnowledgeFact("f7", "Rust", "created_by", "Graydon Hoare", 0.9))

    source_c = KnowledgeSource("src-c", "StackOverflow", reliability=0.75)
    source_c.add_fact(KnowledgeFact("f8", "Python", "paradigm", "OOP", 0.8))
    source_c.add_fact(KnowledgeFact("f9", "Python", "paradigm", "Functional", 0.75))
    source_c.add_fact(KnowledgeFact("f10", "Berlin", "capital_of", "Germany", 0.95))

    print(f"  Source A: {len(source_a.facts)} facts")
    print(f"  Source B: {len(source_b.facts)} facts")
    print(f"  Source C: {len(source_c.facts)} facts")

    # 2. Deduplication
    print("\n[2] Deduplication")
    all_facts = source_a.facts + source_b.facts + source_c.facts
    dedup = DeduplicationEngine()
    duplicates = dedup.find_duplicates(all_facts)
    print(f"  Duplicates found: {len(duplicates)}")
    deduped = dedup.merge_duplicates(all_facts)
    print(f"  After dedup: {len(deduped)} facts (removed {len(all_facts) - len(deduped)})")
    print(f"  Stats: {dedup.get_stats()}")

    # 3. Conflict Detection
    print("\n[3] Conflict Detection")
    resolver = ConflictResolver(ConflictResolution.KEEP_HIGHEST_CONFIDENCE)
    conflicts = resolver.detect_conflicts(deduped)
    print(f"  Conflicts detected: {len(conflicts)}")
    for c in conflicts[:3]:
        print(f"    {c.fact_a.subject}-{c.fact_a.predicate}: '{c.fact_a.object}' vs '{c.fact_b.object}' (severity={c.severity:.2f})")
    print(f"  Stats: {resolver.get_stats()}")

    # 4. Conflict Resolution
    print("\n[4] Conflict Resolution")
    resolved = resolver.resolve(conflicts)
    print(f"  Resolved: {len(resolved)} facts")
    for r in resolved[:3]:
        print(f"    Winner: {r.subject}-{r.predicate}='{r.object}' (conf={r.confidence})")

    # 5. Full Merger
    print("\n[5] Full Merger")
    merger = KnowledgeMerger()
    merged = merger.merge([source_a, source_b, source_c])
    print(f"  Merged facts: {len(merged)}")
    print(f"  Stats: {merger.get_stats()}")

    # 6. Consolidator Pipeline
    print("\n[6] Full Consolidator Pipeline")
    kc = KnowledgeConsolidator()
    kc.add_source(source_a)
    kc.add_source(source_b)
    kc.add_source(source_c)
    consolidated = kc.consolidate()
    print(f"  Consolidated: {len(consolidated)} facts")
    print(f"  Stats: {kc.get_stats()}")

    # 7. Query
    print("\n[7] Query")
    python_facts = kc.query(subject="Python")
    print(f"  Python facts: {len(python_facts)}")
    for f in python_facts:
        print(f"    {f.predicate} = {f.object} (conf={f.confidence}, src={f.source})")

    # 8. Graph Export
    print("\n[8] Graph Export")
    graph = kc.get_graph()
    print(f"  Nodes: {len(graph['nodes'])}")
    print(f"  Edges: {len(graph['edges'])}")
    print(f"  Sample edges: {graph['edges'][:3]}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
