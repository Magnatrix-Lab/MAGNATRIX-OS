"""Ontology Engine — concepts, relations, inference, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum, auto

class RelationType(Enum):
    ISA = auto()
    HASA = auto()
    PARTOF = auto()
    RELATED = auto()
    CAUSES = auto()

@dataclass
class Concept:
    concept_id: str
    label: str
    properties: Dict[str, any] = field(default_factory=dict)
    parents: List[str] = field(default_factory=list)

@dataclass
class Relation:
    source: str
    target: str
    relation_type: RelationType
    weight: float = 1.0

class OntologyEngine:
    def __init__(self):
        self.concepts: Dict[str, Concept] = {}
        self.relations: List[Relation] = []

    def add_concept(self, concept_id: str, label: str, properties: Dict = None, parents: List[str] = None):
        self.concepts[concept_id] = Concept(concept_id, label, properties or {}, parents or [])

    def add_relation(self, source: str, target: str, relation_type: RelationType, weight: float = 1.0):
        self.relations.append(Relation(source, target, relation_type, weight))

    def get_ancestors(self, concept_id: str) -> Set[str]:
        ancestors = set()
        to_visit = [concept_id]
        while to_visit:
            current = to_visit.pop()
            if current in self.concepts:
                for p in self.concepts[current].parents:
                    ancestors.add(p)
                    to_visit.append(p)
        return ancestors

    def get_related(self, concept_id: str, relation_type: Optional[RelationType] = None) -> List[str]:
        related = []
        for r in self.relations:
            if r.source == concept_id and (relation_type is None or r.relation_type == relation_type):
                related.append(r.target)
            if r.relation_type == RelationType.RELATED and r.target == concept_id and (relation_type is None or r.relation_type == relation_type):
                related.append(r.source)
        return related

    def infer(self, concept_id: str) -> Dict:
        return {
            "ancestors": list(self.get_ancestors(concept_id)),
            "related": self.get_related(concept_id),
            "properties": self.concepts.get(concept_id, Concept("", "")).properties
        }

    def query(self, concept_id: str, relation_type: RelationType) -> List[str]:
        return [r.target for r in self.relations if r.source == concept_id and r.relation_type == relation_type]

    def stats(self) -> Dict:
        return {"concepts": len(self.concepts), "relations": len(self.relations), "relation_types": len(set(r.relation_type for r in self.relations))}

def run():
    onto = OntologyEngine()
    onto.add_concept("animal", "Animal", {"alive": True})
    onto.add_concept("mammal", "Mammal", parents=["animal"])
    onto.add_concept("dog", "Dog", {"sound": "bark"}, parents=["mammal"])
    onto.add_concept("cat", "Cat", {"sound": "meow"}, parents=["mammal"])
    onto.add_relation("dog", "bone", RelationType.HASA)
    onto.add_relation("cat", "whisker", RelationType.HASA)
    print(onto.infer("dog"))
    print(onto.query("dog", RelationType.HASA))
    print(onto.stats())

if __name__ == "__main__":
    run()
