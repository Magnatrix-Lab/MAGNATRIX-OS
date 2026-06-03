"""LLM Analogy Finder — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class RelationType(Enum):
    SIMILAR = auto()
    OPPOSITE = auto()
    PART_OF = auto()
    TYPE_OF = auto()
    FUNCTION = auto()

@dataclass
class Concept:
    id: str
    name: str
    attributes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class AnalogyFinder:
    def __init__(self) -> None:
        self._concepts: Dict[str, Concept] = {}
        self._relations: Dict[str, List[tuple]] = {}

    def add_concept(self, concept: Concept) -> None:
        self._concepts[concept.id] = concept

    def add_relation(self, a: str, b: str, relation: RelationType) -> None:
        if a not in self._relations:
            self._relations[a] = []
        self._relations[a].append((b, relation))

    def _similarity(self, c1: Concept, c2: Concept) -> float:
        if not c1.attributes or not c2.attributes:
            return 0.0
        shared = len(set(c1.attributes) & set(c2.attributes))
        total = len(set(c1.attributes) | set(c2.attributes))
        return shared / total if total > 0 else 0.0

    def find_analogies(self, concept_id: str, top_k: int = 3) -> List[tuple]:
        target = self._concepts.get(concept_id)
        if not target:
            return []
        scored = []
        for cid, concept in self._concepts.items():
            if cid != concept_id:
                score = self._similarity(target, concept)
                if score > 0:
                    scored.append((score, concept))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def find_analogical_mapping(self, a: str, b: str, c: str) -> Optional[str]:
        a_concept = self._concepts.get(a)
        b_concept = self._concepts.get(b)
        c_concept = self._concepts.get(c)
        if not all([a_concept, b_concept, c_concept]):
            return None
        a_attrs = set(a_concept.attributes)
        b_attrs = set(b_concept.attributes)
        c_attrs = set(c_concept.attributes)
        a_diff = a_attrs - b_attrs
        target_attrs = c_attrs | a_diff
        best_match = None
        best_score = 0.0
        for cid, concept in self._concepts.items():
            if cid in (a, b, c):
                continue
            score = len(set(concept.attributes) & target_attrs) / len(target_attrs) if target_attrs else 0.0
            if score > best_score:
                best_score = score
                best_match = cid
        return best_match

    def get_stats(self) -> Dict[str, Any]:
        return {"concepts": len(self._concepts), "relations": sum(len(r) for r in self._relations.values())}

def run() -> None:
    print("Analogy Finder test")
    e = AnalogyFinder()
    e.add_concept(Concept("c1", "doctor", ["human", "heals", "medical"]))
    e.add_concept(Concept("c2", "nurse", ["human", "heals", "medical", "care"]))
    e.add_concept(Concept("c3", "mechanic", ["human", "fixes", "machines"]))
    e.add_concept(Concept("c4", "engineer", ["human", "fixes", "builds", "machines"]))
    analogies = e.find_analogies("c1", 2)
    print("  Analogies to doctor: " + str([(a.name, s) for s, a in analogies]))
    mapping = e.find_analogical_mapping("c1", "c2", "c3")
    print("  Analogical mapping: doctor : nurse = mechanic : " + str(mapping))
    print("  Stats: " + str(e.get_stats()))
    print("Analogy Finder test complete.")

if __name__ == "__main__":
    run()
