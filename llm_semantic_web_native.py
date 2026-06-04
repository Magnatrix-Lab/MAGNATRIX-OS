"""Semantic Web / RDF Processor — triple parsing, simple SPARQL-like queries, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import re

@dataclass
class RDFTriple:
    subject: str
    predicate: str
    object: str

class SemanticWebEngine:
    def __init__(self):
        self.triples: List[RDFTriple] = []
        self.namespaces: Dict[str, str] = {}

    def add_namespace(self, prefix: str, uri: str):
        self.namespaces[prefix] = uri

    def expand(self, prefixed: str) -> str:
        for prefix, uri in self.namespaces.items():
            if prefixed.startswith(prefix + ":"):
                return uri + prefixed[len(prefix)+1:]
        return prefixed

    def add_triple(self, subject: str, predicate: str, object: str):
        self.triples.append(RDFTriple(self.expand(subject), self.expand(predicate), self.expand(object)))

    def query_pattern(self, s: Optional[str] = None, p: Optional[str] = None, o: Optional[str] = None) -> List[RDFTriple]:
        results = []
        for t in self.triples:
            if s and t.subject != self.expand(s):
                continue
            if p and t.predicate != self.expand(p):
                continue
            if o and t.object != self.expand(o):
                continue
            results.append(t)
        return results

    def select(self, variables: List[str], pattern: Dict[str, str]) -> List[Dict]:
        results = []
        bindings = {}
        for t in self.triples:
            match = True
            for var, val in pattern.items():
                if var == "?s" and t.subject != self.expand(val):
                    match = False
                if var == "?p" and t.predicate != self.expand(val):
                    match = False
                if var == "?o" and t.object != self.expand(val):
                    match = False
            if match:
                row = {}
                for v in variables:
                    if v == "?s":
                        row[v] = t.subject
                    elif v == "?p":
                        row[v] = t.predicate
                    elif v == "?o":
                        row[v] = t.object
                results.append(row)
        return results

    def describe(self, entity: str) -> List[RDFTriple]:
        return [t for t in self.triples if t.subject == self.expand(entity) or t.object == self.expand(entity)]

    def stats(self) -> Dict:
        return {"triples": len(self.triples), "namespaces": len(self.namespaces), "entities": len(set(t.subject for t in self.triples) | set(t.object for t in self.triples))}

def run():
    sw = SemanticWebEngine()
    sw.add_namespace("foaf", "http://xmlns.com/foaf/0.1/")
    sw.add_namespace("ex", "http://example.org/")
    sw.add_triple("ex:Alice", "foaf:name", "Alice Smith")
    sw.add_triple("ex:Alice", "foaf:knows", "ex:Bob")
    sw.add_triple("ex:Bob", "foaf:name", "Bob Jones")
    print(sw.query_pattern(p="foaf:name"))
    print(sw.select(["?s", "?o"], {"?p": "foaf:name"}))
    print(sw.describe("ex:Alice"))
    print(sw.stats())

if __name__ == "__main__":
    run()
