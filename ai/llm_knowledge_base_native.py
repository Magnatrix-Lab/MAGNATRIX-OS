"""
llm_knowledge_base_native.py
MAGNATRIX-OS Knowledge Base Engine
Native Python, stdlib only.
Provides knowledge storage, fact retrieval, confidence scoring, and knowledge graph construction.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class FactConfidence(Enum):
    CERTAIN = 1.0
    HIGH = 0.8
    MEDIUM = 0.5
    LOW = 0.3
    UNCERTAIN = 0.1


@dataclass
class Fact:
    fact_id: str
    subject: str
    predicate: str
    object: str
    confidence: float
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id, "subject": self.subject, "predicate": self.predicate,
            "object": self.object, "confidence": self.confidence, "sources": self.sources,
        }

    def matches(self, query: str) -> bool:
        q = query.lower()
        return q in self.subject.lower() or q in self.predicate.lower() or q in self.object.lower()


class KnowledgeBaseEngine:
    """Knowledge base with fact storage and retrieval."""

    def __init__(self) -> None:
        self._facts: Dict[str, Fact] = {}
        self._subject_index: Dict[str, Set[str]] = {}
        self._predicate_index: Dict[str, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}

    def add_fact(self, fact: Fact) -> None:
        self._facts[fact.fact_id] = fact
        self._subject_index.setdefault(fact.subject, set()).add(fact.fact_id)
        self._predicate_index.setdefault(fact.predicate, set()).add(fact.fact_id)
        for tag in fact.tags:
            self._tag_index.setdefault(tag, set()).add(fact.fact_id)

    def query(self, subject: Optional[str] = None, predicate: Optional[str] = None,
              object: Optional[str] = None, min_confidence: float = 0.0) -> List[Fact]:
        results = list(self._facts.values())
        if subject:
            fact_ids = self._subject_index.get(subject, set())
            results = [f for f in results if f.fact_id in fact_ids]
        if predicate:
            fact_ids = self._predicate_index.get(predicate, set())
            results = [f for f in results if f.fact_id in fact_ids]
        if object:
            results = [f for f in results if f.object == object]
        results = [f for f in results if f.confidence >= min_confidence]
        return sorted(results, key=lambda f: f.confidence, reverse=True)

    def search(self, query: str, min_confidence: float = 0.0) -> List[Fact]:
        return [f for f in self._facts.values() if f.matches(query) and f.confidence >= min_confidence]

    def get_by_tag(self, tag: str) -> List[Fact]:
        fact_ids = self._tag_index.get(tag, set())
        return [self._facts[fid] for fid in fact_ids if fid in self._facts]

    def get_related(self, subject: str, depth: int = 1) -> List[Fact]:
        facts = self.query(subject=subject)
        if depth <= 1:
            return facts
        related = list(facts)
        for fact in facts:
            related.extend(self.query(subject=fact.object))
        return related

    def get_stats(self) -> Dict[str, Any]:
        return {
            "facts": len(self._facts),
            "subjects": len(self._subject_index),
            "predicates": len(self._predicate_index),
            "avg_confidence": sum(f.confidence for f in self._facts.values()) / max(len(self._facts), 1),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([f.to_dict() for f in self._facts.values()], f, indent=2, default=str)

    def import_facts(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for fd in data:
            fact = Fact(
                fact_id=fd["fact_id"], subject=fd["subject"], predicate=fd["predicate"],
                object=fd["object"], confidence=fd["confidence"], sources=fd.get("sources", []),
                tags=fd.get("tags", []), metadata=fd.get("metadata", {}),
            )
            self.add_fact(fact)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Knowledge Base Engine")
    print("=" * 60)

    engine = KnowledgeBaseEngine()

    facts = [
        Fact("f1", "Paris", "is capital of", "France", 1.0, sources=["wiki"], tags=["geography"]),
        Fact("f2", "France", "is in", "Europe", 1.0, sources=["wiki"], tags=["geography"]),
        Fact("f3", "Python", "is a", "programming language", 1.0, sources=["docs"], tags=["tech"]),
        Fact("f4", "Python", "created by", "Guido van Rossum", 0.9, sources=["docs"], tags=["tech"]),
        Fact("f5", "AI", "is a", "field of computer science", 0.8, sources=["textbook"], tags=["tech"]),
    ]

    for f in facts:
        engine.add_fact(f)

    print("\n--- Query: Paris ---")
    results = engine.query(subject="Paris")
    for f in results:
        print(f"  {f.subject} {f.predicate} {f.object} (conf={f.confidence})")

    print("\n--- Search: programming ---")
    results = engine.search("programming")
    for f in results:
        print(f"  {f.subject} {f.predicate} {f.object}")

    print("\n--- Related to Python ---")
    results = engine.get_related("Python", depth=2)
    for f in results:
        print(f"  {f.subject} {f.predicate} {f.object}")

    print("\n--- By tag: geography ---")
    results = engine.get_by_tag("geography")
    for f in results:
        print(f"  {f.subject} {f.predicate} {f.object}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nKnowledge Base test complete.")


if __name__ == "__main__":
    run()
