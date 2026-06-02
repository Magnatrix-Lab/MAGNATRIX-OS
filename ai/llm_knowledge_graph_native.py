"""Knowledge Graph — Entity extraction, relation mapping, and graph reasoning.

Modul ini menyediakan:
- EntityExtractor untuk ekstrak entities dari text
- RelationExtractor untuk ekstrak relasi antar entities
- KnowledgeGraph untuk graph storage dan traversal
- GraphQuery untuk query dengan pattern matching
- GraphReasoner untuk inference dan multi-hop reasoning
"""

from __future__ import annotations

import json
import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class EntityType(Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    EVENT = "event"
    PRODUCT = "product"
    TECHNOLOGY = "technology"


class RelationType(Enum):
    WORKS_AT = "works_at"
    LOCATED_IN = "located_in"
    CREATED = "created"
    PART_OF = "part_of"
    KNOWS = "knows"
    USES = "uses"
    FOUNDED = "founded"
    LEADS = "leads"


@dataclass
class Entity:
    """Single entity in knowledge graph."""
    entity_id: str
    name: str
    entity_type: EntityType
    aliases: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class Relation:
    """Directed relation between entities."""
    relation_id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class GraphPath:
    """Path through the graph."""
    path_id: str
    entities: List[str]
    relations: List[str]
    confidence: float = 1.0


class EntityExtractor:
    """Extract entities from text."""

    def __init__(self):
        self._patterns: Dict[EntityType, List[str]] = {
            EntityType.PERSON: ["Albert Einstein", "Isaac Newton", "Marie Curie"],
            EntityType.ORGANIZATION: ["Google", "Microsoft", "OpenAI", "Apple", "Tesla"],
            EntityType.LOCATION: ["New York", "London", "Tokyo", "Paris", "Berlin"],
            EntityType.TECHNOLOGY: ["Python", "JavaScript", "AI", "Machine Learning", "Blockchain"],
        }

    def extract(self, text: str) -> List[Entity]:
        entities = []
        for entity_type, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.lower() in text.lower():
                    entities.append(Entity(
                        entity_id=str(uuid.uuid4())[:8],
                        name=pattern,
                        entity_type=entity_type,
                    ))
        return entities

    def extract_with_regex(self, text: str) -> List[Entity]:
        # Simple regex-based extraction
        entities = []
        # Capitalized words as potential entities
        words = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', text)
        for w in set(words):
            if len(w) > 2:
                entities.append(Entity(
                    entity_id=str(uuid.uuid4())[:8],
                    name=w,
                    entity_type=EntityType.CONCEPT,
                ))
        return entities


class RelationExtractor:
    """Extract relations from text."""

    def __init__(self):
        self._templates: Dict[RelationType, List[str]] = {
            RelationType.WORKS_AT: ["works at", "works for", "employed by"],
            RelationType.LOCATED_IN: ["located in", "based in", "headquartered in"],
            RelationType.CREATED: ["created", "developed", "invented", "built"],
            RelationType.FOUNDED: ["founded", "established", "started"],
            RelationType.USES: ["uses", "utilizes", "adopts"],
        }

    def extract(self, text: str, entities: List[Entity]) -> List[Relation]:
        relations = []
        for relation_type, patterns in self._templates.items():
            for pattern in patterns:
                if pattern.lower() in text.lower():
                    # Find closest entity pair
                    for i, src in enumerate(entities):
                        for tgt in entities[i+1:]:
                            relations.append(Relation(
                                relation_id=str(uuid.uuid4())[:8],
                                source_id=src.entity_id,
                                target_id=tgt.entity_id,
                                relation_type=relation_type,
                                confidence=0.7,
                            ))
        return relations


class KnowledgeGraph:
    """Graph storage and traversal."""

    def __init__(self, graph_id: str, name: str):
        self.graph_id = graph_id
        self.name = name
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[str, Relation] = {}
        self._adj: Dict[str, List[str]] = {}  # entity_id -> relation_ids
        self._rev_adj: Dict[str, List[str]] = {}  # reverse

    def add_entity(self, entity: Entity) -> None:
        self._entities[entity.entity_id] = entity
        self._adj.setdefault(entity.entity_id, [])
        self._rev_adj.setdefault(entity.entity_id, [])

    def add_relation(self, relation: Relation) -> bool:
        if relation.source_id not in self._entities or relation.target_id not in self._entities:
            return False
        self._relations[relation.relation_id] = relation
        self._adj.setdefault(relation.source_id, []).append(relation.relation_id)
        self._rev_adj.setdefault(relation.target_id, []).append(relation.relation_id)
        return True

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def get_relation(self, relation_id: str) -> Optional[Relation]:
        return self._relations.get(relation_id)

    def get_neighbors(self, entity_id: str, direction: str = "out") -> List[Tuple[Entity, Relation]]:
        if direction == "out":
            rel_ids = self._adj.get(entity_id, [])
        else:
            rel_ids = self._rev_adj.get(entity_id, [])
        results = []
        for rid in rel_ids:
            rel = self._relations.get(rid)
            if rel:
                other_id = rel.target_id if direction == "out" else rel.source_id
                other = self._entities.get(other_id)
                if other:
                    results.append((other, rel))
        return results

    def traverse(self, start_id: str, max_depth: int = 3) -> List[GraphPath]:
        """BFS traversal returning all paths."""
        paths = []
        visited = set()
        queue = [(start_id, [start_id], [], 1.0)]
        while queue:
            current, entity_path, rel_path, conf = queue.pop(0)
            if len(entity_path) > max_depth + 1:
                continue
            if len(entity_path) > 1:
                paths.append(GraphPath(
                    path_id=str(uuid.uuid4())[:8],
                    entities=entity_path[:],
                    relations=rel_path[:],
                    confidence=conf,
                ))
            for rel_id in self._adj.get(current, []):
                rel = self._relations.get(rel_id)
                if rel and rel.target_id not in entity_path:
                    queue.append((rel.target_id, entity_path + [rel.target_id], rel_path + [rel.relation_id], conf * rel.confidence))
        return paths

    def find_paths(self, source_id: str, target_id: str, max_depth: int = 3) -> List[GraphPath]:
        all_paths = self.traverse(source_id, max_depth)
        return [p for p in all_paths if p.entities and p.entities[-1] == target_id]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entities": len(self._entities),
            "relations": len(self._relations),
            "avg_degree": sum(len(self._adj.get(eid, [])) for eid in self._entities) / max(len(self._entities), 1),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "graph_id": self.graph_id,
                "name": self.name,
                "entities": [{"id": e.entity_id, "name": e.name, "type": e.entity_type.value} for e in self._entities.values()],
                "relations": [{"id": r.relation_id, "source": r.source_id, "target": r.target_id, "type": r.relation_type.value} for r in self._relations.values()],
                "stats": self.get_stats(),
            }, f, indent=2)


class GraphQuery:
    """Pattern matching queries on the graph."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def find_by_type(self, entity_type: EntityType) -> List[Entity]:
        return [e for e in self.graph._entities.values() if e.entity_type == entity_type]

    def find_by_relation(self, relation_type: RelationType) -> List[Relation]:
        return [r for r in self.graph._relations.values() if r.relation_type == relation_type]

    def find_entities_with_relation(self, entity_name: str, relation_type: RelationType) -> List[Entity]:
        entity = None
        for e in self.graph._entities.values():
            if e.name.lower() == entity_name.lower():
                entity = e
                break
        if not entity:
            return []
        results = []
        for rel_id in self.graph._adj.get(entity.entity_id, []):
            rel = self.graph._relations.get(rel_id)
            if rel and rel.relation_type == relation_type:
                target = self.graph._entities.get(rel.target_id)
                if target:
                    results.append(target)
        return results

    def match_pattern(self, pattern: List[Tuple[EntityType, Optional[RelationType]]]) -> List[List[Entity]]:
        """Match path pattern like (Person)-[:WORKS_AT]->(Organization)."""
        if not pattern:
            return []
        # Start with first entity type
        start_type = pattern[0][0]
        starts = self.find_by_type(start_type)
        matches = []
        for start in starts:
            path = [start]
            valid = True
            for i in range(1, len(pattern)):
                expected_type = pattern[i][0]
                expected_rel = pattern[i][1]
                neighbors = self.graph.get_neighbors(start.entity_id, "out")
                found = False
                for neighbor, rel in neighbors:
                    if neighbor.entity_type == expected_type:
                        if expected_rel is None or rel.relation_type == expected_rel:
                            path.append(neighbor)
                            start = neighbor
                            found = True
                            break
                if not found:
                    valid = False
                    break
            if valid and len(path) == len(pattern):
                matches.append(path)
        return matches


class GraphReasoner:
    """Inference and reasoning over the graph."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def infer_relation(self, source_id: str, target_id: str) -> Optional[RelationType]:
        """Infer relation via common neighbors."""
        source_neighbors = set(self.graph._adj.get(source_id, []))
        target_neighbors = set(self.graph._rev_adj.get(target_id, []))
        common = source_neighbors & target_neighbors
        if common:
            rels = [self.graph._relations.get(rid) for rid in common]
            rels = [r for r in rels if r]
            if rels:
                return max(rels, key=lambda r: r.confidence).relation_type
        return None

    def multi_hop_reasoning(self, start_id: str, target_id: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        paths = self.graph.find_paths(start_id, target_id, max_depth)
        results = []
        for path in paths:
            entities = [self.graph.get_entity(eid) for eid in path.entities]
            relations = [self.graph.get_relation(rid) for rid in path.relations]
            results.append({
                "path": " -> ".join([e.name for e in entities if e]),
                "confidence": path.confidence,
                "steps": len(path.relations),
            })
        return results

    def summarize_entity(self, entity_id: str) -> Dict[str, Any]:
        entity = self.graph.get_entity(entity_id)
        if not entity:
            return {}
        out_neighbors = self.graph.get_neighbors(entity_id, "out")
        in_neighbors = self.graph.get_neighbors(entity_id, "in")
        return {
            "entity": entity.name,
            "type": entity.entity_type.value,
            "outgoing_relations": len(out_neighbors),
            "incoming_relations": len(in_neighbors),
            "connected_to": [n.name for n, _ in out_neighbors],
            "connected_from": [n.name for n, _ in in_neighbors],
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("KNOWLEDGE GRAPH DEMO")
    print("=" * 70)

    # 1. Build graph
    print("\n[1] Build Knowledge Graph")
    graph = KnowledgeGraph("kg-1", "Tech Companies")
    entities = [
        Entity("e1", "Sam Altman", EntityType.PERSON),
        Entity("e2", "OpenAI", EntityType.ORGANIZATION),
        Entity("e3", "ChatGPT", EntityType.PRODUCT),
        Entity("e4", "GPT-4", EntityType.TECHNOLOGY),
        Entity("e5", "Microsoft", EntityType.ORGANIZATION),
        Entity("e6", "Satya Nadella", EntityType.PERSON),
        Entity("e7", "San Francisco", EntityType.LOCATION),
    ]
    for e in entities:
        graph.add_entity(e)

    relations = [
        Relation("r1", "e1", "e2", RelationType.FOUNDED, 0.9),
        Relation("r2", "e1", "e2", RelationType.LEADS, 0.95),
        Relation("r3", "e2", "e3", RelationType.CREATED, 1.0),
        Relation("r4", "e2", "e4", RelationType.CREATED, 1.0),
        Relation("r5", "e5", "e2", RelationType.PART_OF, 0.8),  # Microsoft invests in OpenAI
        Relation("r6", "e6", "e5", RelationType.LEADS, 0.95),
        Relation("r7", "e2", "e7", RelationType.LOCATED_IN, 0.9),
    ]
    for r in relations:
        graph.add_relation(r)
    print(f"  Entities: {len(graph._entities)}, Relations: {len(graph._relations)}")

    # 2. Traverse
    print("\n[2] Graph Traversal")
    paths = graph.traverse("e1", max_depth=2)
    print(f"  Paths from Sam Altman (depth 2): {len(paths)}")
    for p in paths[:5]:
        entity_names = [graph.get_entity(eid).name for eid in p.entities if graph.get_entity(eid)]
        print(f"    {' -> '.join(entity_names)} (conf={p.confidence:.2f})")

    # 3. Find paths
    print("\n[3] Find Paths")
    paths = graph.find_paths("e1", "e4", max_depth=3)
    print(f"  Sam Altman -> GPT-4: {len(paths)} paths")
    for p in paths:
        names = [graph.get_entity(eid).name for eid in p.entities if graph.get_entity(eid)]
        print(f"    {' -> '.join(names)}")

    # 4. Query
    print("\n[4] Graph Queries")
    query = GraphQuery(graph)
    orgs = query.find_by_type(EntityType.ORGANIZATION)
    print(f"  Organizations: {[e.name for e in orgs]}")
    founded = query.find_by_relation(RelationType.FOUNDED)
    print(f"  Founded relations: {len(founded)}")
    leads = query.find_entities_with_relation("Sam Altman", RelationType.LEADS)
    print(f"  Sam Altman leads: {[e.name for e in leads]}")

    # 5. Pattern matching
    print("\n[5] Pattern Matching")
    pattern = [
        (EntityType.PERSON, None),
        (EntityType.ORGANIZATION, RelationType.LEADS),
    ]
    matches = query.match_pattern(pattern)
    print(f"  (Person)-[:LEADS]->(Organization): {len(matches)} matches")
    for m in matches:
        print(f"    {m[0].name} -> {m[1].name}")

    # 6. Reasoning
    print("\n[6] Graph Reasoning")
    reasoner = GraphReasoner(graph)
    inferred = reasoner.infer_relation("e6", "e2")
    print(f"  Inferred Satya Nadella -> OpenAI: {inferred.value if inferred else 'None'}")
    reasoning = reasoner.multi_hop_reasoning("e6", "e3", max_depth=3)
    print(f"  Multi-hop Satya Nadella -> ChatGPT:")
    for r in reasoning:
        print(f"    {r['path']} (conf={r['confidence']:.2f})")

    # 7. Entity summary
    print("\n[7] Entity Summary")
    summary = reasoner.summarize_entity("e2")
    print(f"  {summary}")

    # 8. Stats
    print(f"\n[8] Graph Stats")
    print(f"  {graph.get_stats()}")

    # 9. Export
    print("\n[9] Export")
    graph.export("/tmp/knowledge_graph.json")
    print("  Exported to /tmp/knowledge_graph.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
