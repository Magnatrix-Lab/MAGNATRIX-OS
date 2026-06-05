"""Knowledge Graph — triples, inference, SPARQL-like queries, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

@dataclass
class Triple:
    subject: str
    predicate: str
    object: str

class KnowledgeGraph:
    def __init__(self):
        self.triples: List[Triple] = []
        self.index: Dict[str, List[Triple]] = {}

    def add(self, s: str, p: str, o: str):
        t = Triple(s, p, o)
        self.triples.append(t)
        for key in [s, p, o]:
            self.index.setdefault(key, []).append(t)

    def query(self, s: str = None, p: str = None, o: str = None) -> List[Triple]:
        results = self.triples
        if s:
            results = [t for t in results if t.subject == s]
        if p:
            results = [t for t in results if t.predicate == p]
        if o:
            results = [t for t in results if t.object == o]
        return results

    def infer_transitive(self, predicate: str) -> List[Triple]:
        graph = {}
        for t in self.triples:
            if t.predicate == predicate:
                graph.setdefault(t.subject, set()).add(t.object)
        changed = True
        inferred = []
        while changed:
            changed = False
            for s, objs in list(graph.items()):
                for o in list(objs):
                    for o2 in graph.get(o, set()):
                        if o2 not in objs:
                            objs.add(o2)
                            inferred.append(Triple(s, predicate, o2))
                            changed = True
        return inferred

    def stats(self) -> Dict:
        subjects = set(t.subject for t in self.triples)
        predicates = set(t.predicate for t in self.triples)
        objects = set(t.object for t in self.triples)
        return {"triples": len(self.triples), "subjects": len(subjects), "predicates": len(predicates), "objects": len(objects)}

def run():
    kg = KnowledgeGraph()
    kg.add("Alice", "knows", "Bob")
    kg.add("Bob", "knows", "Charlie")
    kg.add("Alice", "age", "30")
    print("Query:", [(t.subject, t.predicate, t.object) for t in kg.query(s="Alice")])
    print("Inferred:", [(t.subject, t.object) for t in kg.infer_transitive("knows")])
    print(kg.stats())

if __name__ == "__main__":
    run()
