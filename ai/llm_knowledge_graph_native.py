"""Knowledge Graph & Inference — Entity extraction, relationship mapping, graph traversal, reasoning.

Modul ini menyediakan:
- KnowledgeGraph untuk node dan edge storage
- EntityExtractor untuk entity/relation extraction
- GraphQuery untuk pattern matching dan traversal
- InferenceEngine untuk deduktif reasoning
- GraphVisualizer untuk graph export (text-based)
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class EntityType(Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    EVENT = "event"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    UNKNOWN = "unknown"


class RelationType(Enum):
    WORKS_AT = "works_at"
    LOCATED_IN = "located_in"
    CREATED = "created"
    PART_OF = "part_of"
    KNOWS = "knows"
    USES = "uses"
    RELATED_TO = "related_to"
    FOLLOWS = "follows"


@dataclass
class Entity:
    """Node dalam knowledge graph."""
    id: str
    name: str
    entity_type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """Edge dalam knowledge graph."""
    id: str
    source: str
    target: str
    relation_type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class GraphQuery:
    """Query pattern untuk graph."""
    pattern: str  # e.g., "(PERSON)-[:WORKS_AT]->(ORGANIZATION)"
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceRule:
    """Rule untuk deduktif reasoning."""
    rule_id: str
    premises: List[Tuple[str, RelationType, str]]  # (entity_type, relation, entity_type)
    conclusion: Tuple[str, RelationType, str]
    confidence: float = 1.0


class KnowledgeGraph:
    """Knowledge graph dengan entity dan relation storage."""

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._relations: List[Relation] = []
        self._adj: Dict[str, List[Relation]] = {}  # source -> outgoing relations
        self._inv_adj: Dict[str, List[Relation]] = {}  # target -> incoming relations

    def add_entity(self, entity: Entity) -> Entity:
        self._entities[entity.id] = entity
        self._adj.setdefault(entity.id, [])
        self._inv_adj.setdefault(entity.id, [])
        return entity

    def add_relation(self, relation: Relation) -> Relation:
        self._relations.append(relation)
        self._adj.setdefault(relation.source, []).append(relation)
        self._inv_adj.setdefault(relation.target, []).append(relation)
        return relation

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def get_relations(self, entity_id: str, direction: str = "out") -> List[Relation]:
        if direction == "out":
            return self._adj.get(entity_id, [])
        elif direction == "in":
            return self._inv_adj.get(entity_id, [])
        return self._adj.get(entity_id, []) + self._inv_adj.get(entity_id, [])

    def find_entities(self, entity_type: Optional[EntityType] = None, name_pattern: Optional[str] = None) -> List[Entity]:
        results = list(self._entities.values())
        if entity_type:
            results = [e for e in results if e.entity_type == entity_type]
        if name_pattern:
            results = [e for e in results if name_pattern.lower() in e.name.lower()]
        return results

    def find_relations(self, source: Optional[str] = None, target: Optional[str] = None, relation_type: Optional[RelationType] = None) -> List[Relation]:
        results = self._relations
        if source:
            results = [r for r in results if r.source == source]
        if target:
            results = [r for r in results if r.target == target]
        if relation_type:
            results = [r for r in results if r.relation_type == relation_type]
        return results

    def traverse(self, start_id: str, depth: int = 2, relation_types: Optional[List[RelationType]] = None) -> List[Tuple[str, str, str, float]]:
        """BFS traversal returning (source, relation, target, confidence) paths."""
        visited = {start_id}
        queue = [(start_id, 0)]
        paths = []
        while queue:
            current, d = queue.pop(0)
            if d >= depth:
                continue
            for rel in self._adj.get(current, []):
                if relation_types and rel.relation_type not in relation_types:
                    continue
                paths.append((current, rel.relation_type.value, rel.target, rel.confidence))
                if rel.target not in visited:
                    visited.add(rel.target)
                    queue.append((rel.target, d + 1))
        return paths

    def shortest_path(self, start_id: str, end_id: str) -> List[Relation]:
        """Find shortest path antara dua entities."""
        if start_id not in self._entities or end_id not in self._entities:
            return []
        queue = [(start_id, [])]
        visited = {start_id}
        while queue:
            current, path = queue.pop(0)
            if current == end_id:
                return path
            for rel in self._adj.get(current, []):
                if rel.target not in visited:
                    visited.add(rel.target)
                    queue.append((rel.target, path + [rel]))
        return []

    def get_neighbors(self, entity_id: str, relation_type: Optional[RelationType] = None) -> List[Entity]:
        rels = self._adj.get(entity_id, [])
        if relation_type:
            rels = [r for r in rels if r.relation_type == relation_type]
        return [self._entities[r.target] for r in rels if r.target in self._entities]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entities": len(self._entities),
            "relations": len(self._relations),
            "entity_types": {t.value: sum(1 for e in self._entities.values() if e.entity_type == t) for t in EntityType},
            "relation_types": {t.value: sum(1 for r in self._relations if r.relation_type == t) for t in RelationType},
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "entities": {
                    e.id: {"name": e.name, "type": e.entity_type.value, "properties": e.properties}
                    for e in self._entities.values()
                },
                "relations": [
                    {"source": r.source, "target": r.target, "type": r.relation_type.value, "confidence": r.confidence}
                    for r in self._relations
                ]
            }, f, indent=2)

    def to_text(self) -> str:
        lines = ["Knowledge Graph:", f"  Entities: {len(self._entities)}", f"  Relations: {len(self._relations)}", ""]
        for e in self._entities.values():
            lines.append(f"  [{e.entity_type.value}] {e.name} (id: {e.id})")
            for r in self._adj.get(e.id, []):
                target = self._entities.get(r.target)
                if target:
                    lines.append(f"    -> {r.relation_type.value} -> {target.name}")
        return "\n".join(lines)


class EntityExtractor:
    """Extract entities dan relations dari text."""

    def __init__(self):
        self._patterns = {
            EntityType.PERSON: [r"\b([A-Z][a-z]+\s[A-Z][a-z]+)\b", r"\b([A-Z][a-z]+)\b"],
            EntityType.ORGANIZATION: [r"\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*)*(?:\s+(?:Inc|Corp|Ltd|LLC|Company|Organization))?)\b"],
            EntityType.LOCATION: [r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s*(?:City|State|Country|Island)?)\b"],
            EntityType.TECHNOLOGY: [r"\b(Python|JavaScript|TypeScript|Rust|Go|Java|C\+\+|React|TensorFlow|PyTorch|Docker|Kubernetes)\b"],
        }

    def extract(self, text: str) -> Tuple[List[Entity], List[Relation]]:
        entities = []
        relations = []
        seen = set()
        # Simple extraction (not production quality, for demo only)
        import re
        words = text.split()
        for i, word in enumerate(words):
            clean = word.strip(".,;:!?()")
            if clean and clean[0].isupper() and clean not in seen and len(clean) > 2:
                if i > 0 and words[i-1].lower() in ("mr", "mrs", "ms", "dr"):
                    e_type = EntityType.PERSON
                elif any(t in clean.lower() for t in ["corp", "inc", "ltd", "company"]):
                    e_type = EntityType.ORGANIZATION
                elif clean in ["Python", "JavaScript", "TensorFlow", "Docker"]:
                    e_type = EntityType.TECHNOLOGY
                else:
                    e_type = EntityType.UNKNOWN
                eid = f"e{len(entities)}"
                entities.append(Entity(eid, clean, e_type))
                seen.add(clean)
        return entities, relations


class InferenceEngine:
    """Deduktif reasoning pada knowledge graph."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self._rules: List[InferenceRule] = []

    def add_rule(self, rule: InferenceRule) -> None:
        self._rules.append(rule)

    def infer(self, entity_id: Optional[str] = None) -> List[Tuple[str, Relation, float]]:
        """Apply rules untuk infer new relations."""
        inferred = []
        for rule in self._rules:
            # Find matching premise patterns
            matches = self._find_matches(rule.premises)
            for match in matches:
                # Apply conclusion
                source, rel_type, target = rule.conclusion
                # Substitute variables
                source_id = match.get(source, source)
                target_id = match.get(target, target)
                if source_id in self.graph._entities and target_id in self.graph._entities:
                    rel = Relation(
                        id=f"inf-{len(inferred)}",
                        source=source_id,
                        target=target_id,
                        relation_type=rel_type,
                        confidence=rule.confidence
                    )
                    inferred.append((rule.rule_id, rel, rule.confidence))
        return inferred

    def _find_matches(self, premises: List[Tuple[str, RelationType, str]]) -> List[Dict[str, str]]:
        matches = []
        for rel in self.graph._relations:
            mapping = {}
            for prem in premises:
                etype, rtype, etarget = prem
                if rel.relation_type == rtype:
                    source = self.graph._entities.get(rel.source)
                    target = self.graph._entities.get(rel.target)
                    if source and target:
                        mapping[etype] = source.id
                        mapping[etarget] = target.id
                        matches.append(mapping)
        return matches

    def transitive_closure(self, relation_type: RelationType) -> List[Tuple[str, str]]:
        """Find all pairs connected by transitive relation."""
        pairs = set()
        for eid in self.graph._entities:
            paths = self.graph.traverse(eid, depth=5, relation_types=[relation_type])
            for _, _, target, _ in paths:
                pairs.add((eid, target))
        return list(pairs)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("KNOWLEDGE GRAPH & INFERENCE DEMO")
    print("=" * 70)

    # 1. Build graph
    print("\n[1] Build Knowledge Graph")
    kg = KnowledgeGraph()
    entities = [
        Entity("e1", "Alice", EntityType.PERSON, {"age": 30}),
        Entity("e2", "Bob", EntityType.PERSON, {"age": 28}),
        Entity("e3", "TechCorp", EntityType.ORGANIZATION, {"founded": 2010}),
        Entity("e4", "StartupX", EntityType.ORGANIZATION, {"founded": 2020}),
        Entity("e5", "Boston", EntityType.LOCATION),
        Entity("e6", "Python", EntityType.TECHNOLOGY),
        Entity("e7", "TensorFlow", EntityType.TECHNOLOGY),
    ]
    for e in entities:
        kg.add_entity(e)

    relations = [
        Relation("r1", "e1", "e3", RelationType.WORKS_AT),
        Relation("r2", "e2", "e4", RelationType.WORKS_AT),
        Relation("r3", "e3", "e5", RelationType.LOCATED_IN),
        Relation("r4", "e4", "e5", RelationType.LOCATED_IN),
        Relation("r5", "e1", "e6", RelationType.USES),
        Relation("r6", "e3", "e7", RelationType.USES),
    ]
    for r in relations:
        kg.add_relation(r)

    print(kg.to_text())
    print(f"  Stats: {kg.get_stats()}")

    # 2. Traversal
    print("\n[2] Graph Traversal")
    paths = kg.traverse("e1", depth=2)
    print(f"  From Alice (depth 2):")
    for src, rel, tgt, conf in paths:
        src_name = kg.get_entity(src).name if kg.get_entity(src) else src
        tgt_name = kg.get_entity(tgt).name if kg.get_entity(tgt) else tgt
        print(f"    {src_name} --{rel}--> {tgt_name} (conf: {conf})")

    # 3. Shortest path
    print("\n[3] Shortest Path")
    sp = kg.shortest_path("e1", "e5")
    print(f"  Alice to Boston: {len(sp)} hops")
    for r in sp:
        src = kg.get_entity(r.source).name
        tgt = kg.get_entity(r.target).name
        print(f"    {src} -> {r.relation_type.value} -> {tgt}")

    # 4. Query
    print("\n[4] Query")
    orgs = kg.find_entities(entity_type=EntityType.ORGANIZATION)
    print(f"  Organizations: {[e.name for e in orgs]}")
    works_at = kg.find_relations(relation_type=RelationType.WORKS_AT)
    print(f"  WORKS_AT relations: {len(works_at)}")

    # 5. Inference
    print("\n[5] Inference")
    infer = InferenceEngine(kg)
    infer.add_rule(InferenceRule(
        "rule1",
        [("PERSON", RelationType.WORKS_AT, "ORG")],
        ("PERSON", RelationType.KNOWS, "ORG"),
        0.8
    ))
    inferred = infer.infer()
    print(f"  Inferred relations: {len(inferred)}")
    for rule_id, rel, conf in inferred:
        src = kg.get_entity(rel.source).name
        tgt = kg.get_entity(rel.target).name
        print(f"    [{rule_id}] {src} -> {rel.relation_type.value} -> {tgt} (conf: {conf})")

    # 6. Export
    print("\n[6] Export")
    kg.export("/tmp/knowledge_graph.json")
    print(f"  Exported to /tmp/knowledge_graph.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
