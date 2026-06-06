#!/usr/bin/env python3
"""
Knowledge Graph Engine for MAGNATRIX-OS
Semantic memory layer: triple store, entity extraction, reasoning, inference.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class LiteralType(enum.Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    URI = "uri"


@dataclasses.dataclass
class Triple:
    subject: str
    predicate: str
    object: Any
    object_type: LiteralType = LiteralType.STRING
    confidence: float = 1.0
    timestamp: float = dataclasses.field(default_factory=time.time)
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "object_type": self.object_type.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "source": self.source,
        }


@dataclasses.dataclass
class Entity:
    uri: str
    label: str
    entity_type: str
    properties: Dict[str, Any] = dataclasses.field(default_factory=dict)
    aliases: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "label": self.label,
            "type": self.entity_type,
            "properties": self.properties,
            "aliases": self.aliases,
        }


class TripleStore:
    """In-memory triple store with multi-indexing."""

    def __init__(self) -> None:
        self._triples: List[Triple] = []
        # Indexes
        self._by_subject: Dict[str, List[int]] = {}
        self._by_predicate: Dict[str, List[int]] = {}
        self._by_object: Dict[str, List[int]] = {}
        self._by_sp: Dict[Tuple[str, str], List[int]] = {}
        self._by_po: Dict[Tuple[str, str], List[int]] = {}

    def add(self, triple: Triple) -> None:
        idx = len(self._triples)
        self._triples.append(triple)

        # Update indexes
        self._by_subject.setdefault(triple.subject, []).append(idx)
        self._by_predicate.setdefault(triple.predicate, []).append(idx)
        obj_key = str(triple.object)
        self._by_object.setdefault(obj_key, []).append(idx)
        self._by_sp.setdefault((triple.subject, triple.predicate), []).append(idx)
        self._by_po.setdefault((triple.predicate, obj_key), []).append(idx)

    def query(self, subject: Optional[str] = None, predicate: Optional[str] = None, object: Optional[str] = None) -> List[Triple]:
        """Triple pattern matching."""
        if subject and predicate:
            idxs = self._by_sp.get((subject, predicate), [])
        elif predicate and object:
            idxs = self._by_po.get((predicate, str(object)), [])
        elif subject:
            idxs = self._by_subject.get(subject, [])
        elif predicate:
            idxs = self._by_predicate.get(predicate, [])
        elif object:
            idxs = self._by_object.get(str(object), [])
        else:
            return list(self._triples)

        # Filter
        result = []
        for idx in idxs:
            t = self._triples[idx]
            if subject and t.subject != subject:
                continue
            if predicate and t.predicate != predicate:
                continue
            if object and str(t.object) != str(object):
                continue
            result.append(t)
        return result

    def count(self) -> int:
        return len(self._triples)

    def get_subjects(self) -> Set[str]:
        return set(self._by_subject.keys())

    def get_predicates(self) -> Set[str]:
        return set(self._by_predicate.keys())

    def get_objects(self) -> Set[str]:
        return set(self._by_object.keys())

    def to_dict(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._triples]


class EntityExtractor:
    """Extract entities from text using patterns."""

    # Named entity patterns
    PERSON_PATTERNS = [
        re.compile(r'([A-Z][a-z]+\s+[A-Z][a-z]+)'),  # Two capitalized words
    ]

    ORG_PATTERNS = [
        re.compile(r'([A-Z][a-zA-Z]+\s+(Inc|Corp|Ltd|LLC|Company|Organization))'),
    ]

    LOCATION_PATTERNS = [
        re.compile(r'\b(New York|London|Tokyo|Paris|Berlin|Singapore|Sydney|Jakarta)\b'),
    ]

    RELATION_PATTERNS = {
        "works_at": re.compile(r'(?i)(\w+)\s+(works?\s+at|employed\s+by|job\s+at)\s+([A-Z][\w\s]+)'),
        "created": re.compile(r'(?i)(\w+)\s+(created|built|developed|made)\s+([\w\s]+)'),
        "is_a": re.compile(r'(?i)(\w+)\s+(is\s+a|is\s+an)\s+([\w\s]+)'),
        "located_in": re.compile(r'(?i)(\w+)\s+(is\s+located\s+in|is\s+in)\s+([\w\s]+)'),
        "causes": re.compile(r'(?i)(\w+)\s+(causes|leads\s+to|results\s+in)\s+([\w\s]+)'),
    }

    def extract_entities(self, text: str) -> List[Entity]:
        entities = []
        seen = set()

        # Extract persons
        for pattern in self.PERSON_PATTERNS:
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                if name not in seen:
                    seen.add(name)
                    entities.append(Entity(uri=f"person:{name.lower().replace(' ', '_')}", label=name, entity_type="person"))

        # Extract organizations
        for pattern in self.ORG_PATTERNS:
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                if name not in seen:
                    seen.add(name)
                    entities.append(Entity(uri=f"org:{name.lower().replace(' ', '_')}", label=name, entity_type="organization"))

        # Extract locations
        for pattern in self.LOCATION_PATTERNS:
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                if name not in seen:
                    seen.add(name)
                    entities.append(Entity(uri=f"loc:{name.lower().replace(' ', '_')}", label=name, entity_type="location"))

        return entities

    def extract_relations(self, text: str) -> List[Triple]:
        triples = []
        for relation, pattern in self.RELATION_PATTERNS.items():
            for match in pattern.finditer(text):
                subject = match.group(1).strip()
                obj = match.group(3).strip() if len(match.groups()) > 2 else match.group(2).strip()
                triples.append(Triple(
                    subject=f"entity:{subject.lower()}",
                    predicate=relation,
                    object=obj,
                    confidence=0.7,
                ))
        return triples


class GraphQueryEngine:
    """Query and traverse the knowledge graph."""

    def __init__(self, store: TripleStore) -> None:
        self._store = store

    def find_path(self, start: str, end: str, max_depth: int = 5) -> Optional[List[Triple]]:
        """Find shortest path between two entities using BFS."""
        visited = {start}
        queue = [(start, [])]

        while queue:
            current, path = queue.pop(0)
            if current == end and path:
                return path

            if len(path) >= max_depth:
                continue

            triples = self._store.query(subject=current)
            for t in triples:
                next_node = str(t.object)
                if next_node not in visited:
                    visited.add(next_node)
                    queue.append((next_node, path + [t]))

        return None

    def get_neighbors(self, entity: str, predicate: Optional[str] = None) -> List[Triple]:
        return self._store.query(subject=entity, predicate=predicate)

    def get_reverse_neighbors(self, entity: str, predicate: Optional[str] = None) -> List[Triple]:
        return self._store.query(predicate=predicate, object=entity)

    def traverse(self, start: str, depth: int = 2) -> Dict[str, List[Dict[str, Any]]]:
        """BFS traversal up to given depth."""
        result = {start: []}
        visited = {start}
        current_level = [start]

        for d in range(depth):
            next_level = []
            for entity in current_level:
                triples = self._store.query(subject=entity)
                for t in triples:
                    result.setdefault(entity, []).append(t.to_dict())
                    next_node = str(t.object)
                    if next_node not in visited:
                        visited.add(next_node)
                        next_level.append(next_node)
            current_level = next_level

        return result


class InferenceEngine:
    """Simple rule-based inference."""

    def __init__(self, store: TripleStore) -> None:
        self._store = store
        self._rules = []

    def add_rule(self, name: str, pattern: Tuple[str, str, str], conclusion: Tuple[str, str, str]) -> None:
        self._rules.append({"name": name, "pattern": pattern, "conclusion": conclusion})

    def infer(self) -> List[Triple]:
        """Apply inference rules and return new triples."""
        new_triples = []

        for rule in self._rules:
            pattern = rule["pattern"]
            matches = self._store.query(
                subject=pattern[0] if pattern[0] != "?" else None,
                predicate=pattern[1] if pattern[1] != "?" else None,
                object=pattern[2] if pattern[2] != "?" else None,
            )

            for match in matches:
                # Bind conclusion
                subject = rule["conclusion"][0].replace("?s", match.subject)
                predicate = rule["conclusion"][1].replace("?p", match.predicate)
                obj = rule["conclusion"][2].replace("?o", str(match.object))

                # Check if already exists
                existing = self._store.query(subject=subject, predicate=predicate, object=obj)
                if not existing:
                    new_triples.append(Triple(
                        subject=subject, predicate=predicate, object=obj,
                        confidence=0.6, source=f"inference:{rule['name']}"
                    ))

        return new_triples

    def transitive_closure(self, predicate: str) -> List[Triple]:
        """Compute transitive closure for a predicate."""
        new_triples = []
        # Find all (A, pred, B) and (B, pred, C) -> infer (A, pred, C)
        triples = self._store.query(predicate=predicate)

        chain = {}
        for t in triples:
            chain.setdefault(t.subject, set()).add(str(t.object))

        # Expand
        changed = True
        while changed:
            changed = False
            for a in list(chain.keys()):
                for b in list(chain[a]):
                    if b in chain:
                        for c in chain[b]:
                            if c not in chain[a]:
                                chain[a].add(c)
                                new_triples.append(Triple(
                                    subject=a, predicate=predicate, object=c,
                                    confidence=0.5, source="inference:transitive"
                                ))
                                changed = True

        return new_triples


class GraphExporter:
    """Export knowledge graph to various formats."""

    def __init__(self, store: TripleStore) -> None:
        self._store = store

    def to_turtle(self) -> str:
        """Export to Turtle-like format."""
        lines = ["@prefix ex: <http://example.org/> ."]
        for t in self._store._triples:
            obj_str = f'"{t.object}"' if t.object_type == LiteralType.STRING else str(t.object)
            lines.append(f"ex:{t.subject} ex:{t.predicate} {obj_str} .")
        return "\n".join(lines)

    def to_jsonld(self) -> Dict[str, Any]:
        """Export to JSON-LD."""
        return {
            "@context": {"ex": "http://example.org/"},
            "@graph": [
                {
                    "@id": f"ex:{t.subject}",
                    t.predicate: {"@value": t.object, "@type": t.object_type.value},
                }
                for t in self._store._triples
            ],
        }

    def to_dot(self) -> str:
        """Export to Graphviz DOT format."""
        lines = ["digraph KnowledgeGraph {"]
        seen = set()
        for t in self._store._triples:
            s = t.subject.replace("-", "_").replace(":", "_")
            o = str(t.object).replace("-", "_").replace(":", "_")
            if (s, o) not in seen:
                seen.add((s, o))
                lines.append(f'  "{s}" -> "{o}" [label="{t.predicate}"];')
        lines.append("}")
        return "\n".join(lines)


class KnowledgeGraphEngine:
    """Main knowledge graph orchestrator."""

    def __init__(self, persistence_path: str = "./knowledge_graph.json") -> None:
        self.store = TripleStore()
        self.extractor = EntityExtractor()
        self.query_engine = GraphQueryEngine(self.store)
        self.inference = InferenceEngine(self.store)
        self.exporter = GraphExporter(self.store)
        self._persistence_path = persistence_path
        self._entities: Dict[str, Entity] = {}

    def add_triple(self, subject: str, predicate: str, object: Any, confidence: float = 1.0) -> None:
        triple = Triple(subject=subject, predicate=predicate, object=object, confidence=confidence)
        self.store.add(triple)

    def ingest_text(self, text: str, source: str = "") -> Dict[str, Any]:
        """Extract entities and relations from text."""
        entities = self.extractor.extract_entities(text)
        relations = self.extractor.extract_relations(text)

        # Add to store
        for e in entities:
            self._entities[e.uri] = e
            self.add_triple(e.uri, "label", e.label, confidence=0.9)
            self.add_triple(e.uri, "type", e.entity_type, confidence=0.9)

        for r in relations:
            r.source = source
            self.store.add(r)

        return {
            "entities": len(entities),
            "relations": len(relations),
            "total_triples": self.store.count(),
        }

    def query(self, subject: Optional[str] = None, predicate: Optional[str] = None, object: Optional[str] = None) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.store.query(subject, predicate, object)]

    def find_path(self, start: str, end: str) -> Optional[List[Dict[str, Any]]]:
        path = self.query_engine.find_path(start, end)
        if path:
            return [t.to_dict() for t in path]
        return None

    def infer(self) -> List[Dict[str, Any]]:
        # Add default rules
        self.inference.add_rule("type_inheritance", ("?", "type", "?"), ("?s", "has_type", "?o"))
        self.inference.add_rule("label_lookup", ("?", "label", "?"), ("?s", "has_label", "?o"))

        new_triples = self.inference.infer()
        for t in new_triples:
            self.store.add(t)
        return [t.to_dict() for t in new_triples]

    def save(self) -> None:
        data = {
            "triples": self.store.to_dict(),
            "entities": {k: v.to_dict() for k, v in self._entities.items()},
        }
        with open(self._persistence_path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self) -> None:
        if not os.path.exists(self._persistence_path):
            return
        with open(self._persistence_path, "r") as f:
            data = json.load(f)
        for t in data.get("triples", []):
            self.store.add(Triple(
                subject=t["subject"],
                predicate=t["predicate"],
                object=t["object"],
                object_type=LiteralType(t.get("object_type", "string")),
                confidence=t.get("confidence", 1.0),
            ))

    def export(self, fmt: str = "turtle") -> str:
        if fmt == "turtle":
            return self.exporter.to_turtle()
        elif fmt == "dot":
            return self.exporter.to_dot()
        elif fmt == "json":
            return json.dumps(self.exporter.to_jsonld(), indent=2)
        return ""

    def stats(self) -> Dict[str, Any]:
        return {
            "triples": self.store.count(),
            "subjects": len(self.store.get_subjects()),
            "predicates": len(self.store.get_predicates()),
            "objects": len(self.store.get_objects()),
            "entities": len(self._entities),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== MAGNATRIX-OS Knowledge Graph Engine Demo ===\n")

    engine = KnowledgeGraphEngine()

    # Demo 1: Ingest text
    print("--- Demo 1: Text Ingestion ---")
    text = """
    Alice works at Google. Bob is a software engineer at Microsoft.
    Alice created the KnowledgeGraph engine. Bob is located in Seattle.
    Google is located in Mountain View. Microsoft causes competition with Google.
    """
    result = engine.ingest_text(text, source="demo")
    print(f"  Entities: {result['entities']}, Relations: {result['relations']}")
    print(f"  Total triples: {result['total_triples']}")
    print()

    # Demo 2: Query
    print("--- Demo 2: Triple Queries ---")
    print(f"  Alice works_at: {engine.query(subject='entity:alice', predicate='works_at')}")
    print(f"  All created relations: {len(engine.query(predicate='created'))}")
    print()

    # Demo 3: Path finding
    print("--- Demo 3: Path Finding ---")
    # Add path: Alice -> works_at -> Google
    path = engine.find_path("entity:alice", "org:google")
    if path:
        print(f"  Path from Alice to Google: {len(path)} hops")
        for t in path:
            print(f"    {t['subject']} --{t['predicate']}--> {t['object']}")
    print()

    # Demo 4: Inference
    print("--- Demo 4: Inference ---")
    inferred = engine.infer()
    print(f"  Inferred triples: {len(inferred)}")
    print()

    # Demo 5: Export
    print("--- Demo 5: Export ---")
    dot = engine.export("dot")
    print(f"  DOT format: {len(dot)} chars")
    print(f"  First 3 lines:")
    for line in dot.split("\n")[:4]:
        print(f"    {line}")
    print()

    # Demo 6: Stats
    print("--- Demo 6: Stats ---")
    stats = engine.stats()
    print(f"  Triples: {stats['triples']}")
    print(f"  Subjects: {stats['subjects']}")
    print(f"  Predicates: {stats['predicates']}")
    print(f"  Entities: {stats['entities']}")
    print()

    # Demo 7: Multi-hop
    print("--- Demo 7: Multi-hop Reasoning ---")
    # Add: Alice -> works_at -> Google -> located_in -> Mountain View
    # Can we find path from Alice to Mountain View?
    engine.add_triple("entity:alice", "works_at", "org:google")
    engine.add_triple("org:google", "located_in", "loc:mountain_view")

    path2 = engine.find_path("entity:alice", "loc:mountain_view", max_depth=3)
    if path2:
        print(f"  Path from Alice to Mountain View: {len(path2)} hops")
    else:
        print("  No direct path found (may need transitive inference)")
    print()

    print("=== Knowledge Graph Engine Demo Complete ===")


if __name__ == "__main__":
    _demo()
