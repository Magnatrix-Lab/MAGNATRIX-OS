"""Knowledge Graph - RDF-style triples for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from collections import defaultdict

@dataclass
class KnowledgeGraph:
    triples: List[Tuple[str, str, str]] = field(default_factory=list)
    index: Dict[str, Dict[str, Set[str]]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(set)))

    def add(self, subject: str, predicate: str, obj: str) -> None:
        self.triples.append((subject, predicate, obj))
        self.index[subject][predicate].add(obj)

    def query(self, subject: str = None, predicate: str = None, obj: str = None) -> List[Tuple[str, str, str]]:
        results = []
        for s, p, o in self.triples:
            if (subject is None or s == subject) and (predicate is None or p == predicate) and (obj is None or o == obj):
                results.append((s, p, o))
        return results

    def infer_transitive(self, predicate: str) -> List[Tuple[str, str, str]]:
        inferred = []
        for s1, p1, o1 in self.triples:
            if p1 == predicate:
                for s2, p2, o2 in self.triples:
                    if p2 == predicate and o1 == s2:
                        inferred.append((s1, predicate, o2))
        return inferred

    def stats(self) -> dict:
        subjects = set(s for s, _, _ in self.triples)
        predicates = set(p for _, p, _ in self.triples)
        objects = set(o for _, _, o in self.triples)
        return {"triples": len(self.triples), "subjects": len(subjects), "predicates": len(predicates), "objects": len(objects)}

def run():
    kg = KnowledgeGraph()
    kg.add("Alice", "knows", "Bob")
    kg.add("Bob", "knows", "Charlie")
    kg.add("Alice", "works_at", "Company")
    print("Query knows:", kg.query(predicate="knows"))
    print("Transitive:", kg.infer_transitive("knows"))
    print("Stats:", kg.stats())

if __name__ == "__main__": run()
