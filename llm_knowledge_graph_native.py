"""Knowledge Graph — triples, paths, and simple queries, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum, auto

@dataclass
class Triple:
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0

class KnowledgeGraph:
    def __init__(self):
        self.triples: List[Triple] = []
        self.index_spo: Dict[str, List[Triple]] = {}
        self.index_ops: Dict[str, List[Triple]] = {}

    def add(self, subject: str, predicate: str, object: str, confidence: float = 1.0):
        t = Triple(subject, predicate, object, confidence)
        self.triples.append(t)
        if subject not in self.index_spo:
            self.index_spo[subject] = []
        self.index_spo[subject].append(t)
        if object not in self.index_ops:
            self.index_ops[object] = []
        self.index_ops[object].append(t)

    def query(self, subject: Optional[str] = None, predicate: Optional[str] = None, object: Optional[str] = None) -> List[Triple]:
        results = self.triples
        if subject:
            results = [t for t in results if t.subject == subject]
        if predicate:
            results = [t for t in results if t.predicate == predicate]
        if object:
            results = [t for t in results if t.object == object]
        return results

    def get_neighbors(self, entity: str) -> List[str]:
        neighbors = []
        for t in self.index_spo.get(entity, []):
            neighbors.append(t.object)
        for t in self.index_ops.get(entity, []):
            neighbors.append(t.subject)
        return list(set(neighbors))

    def find_path(self, start: str, end: str, max_depth: int = 5) -> Optional[List[str]]:
        visited = {start}
        queue = [(start, [start])]
        while queue:
            current, path = queue.pop(0)
            if current == end:
                return path
            if len(path) >= max_depth:
                continue
            for t in self.index_spo.get(current, []):
                if t.object not in visited:
                    visited.add(t.object)
                    queue.append((t.object, path + [t.object]))
        return None

    def get_entities(self) -> Set[str]:
        return set(t.subject for t in self.triples) | set(t.object for t in self.triples)

    def get_predicates(self) -> Set[str]:
        return set(t.predicate for t in self.triples)

    def stats(self) -> Dict:
        return {"triples": len(self.triples), "entities": len(self.get_entities()), "predicates": len(self.get_predicates())}

def run():
    kg = KnowledgeGraph()
    kg.add("Alice", "knows", "Bob")
    kg.add("Bob", "knows", "Charlie")
    kg.add("Charlie", "works_at", "Acme")
    kg.add("Alice", "works_at", "Acme")
    print(kg.query(predicate="knows"))
    print(kg.get_neighbors("Bob"))
    print(kg.find_path("Alice", "Acme"))
    print(kg.stats())

if __name__ == "__main__":
    run()
