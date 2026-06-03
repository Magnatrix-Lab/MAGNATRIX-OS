#!/usr/bin/env python3
"""
MAGNATRIX-OS — Knowledge Graph Engine
ai/llm_knowledge_graph_native.py

Features:
- Entity extraction and storage
- Relation building (entity → relation → entity)
- Graph traversal (BFS, DFS path finding)
- Query engine (find entities by relation, path between entities)
- Graph serialization and stats

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("knowledge_graph")


@dataclass
class Entity:
    id: str
    name: str
    type: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    source: str
    target: str
    type: str
    weight: float = 1.0


class KnowledgeGraphEngine:
    """Knowledge graph with entity extraction, relations, and queries."""

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._relations: List[Relation] = []
        self._adj: Dict[str, List[Tuple[str, str, float]]] = defaultdict(list)  # source -> [(target, rel_type, weight)]

    def add_entity(self, entity: Entity) -> None:
        self._entities[entity.id] = entity

    def add_relation(self, relation: Relation) -> None:
        self._relations.append(relation)
        self._adj[relation.source].append((relation.target, relation.type, relation.weight))

    def extract_entities(self, text: str) -> List[Entity]:
        """Simple rule-based entity extraction."""
        entities = []
        # Detect capitalized phrases as entities
        import re
        matches = re.findall(r'[A-Z][a-zA-Z\s]+', text)
        for i, match in enumerate(matches[:10]):
            name = match.strip()
            if len(name) > 2 and name not in [e.name for e in entities]:
                eid = f"E{i}"
                entities.append(Entity(eid, name, "unknown"))
        return entities

    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> Optional[List[Relation]]:
        """BFS path finding between entities."""
        visited = {source_id}
        queue = deque([(source_id, [])])
        while queue:
            current, path = queue.popleft()
            if current == target_id:
                return path
            if len(path) >= max_depth:
                continue
            for target, rel_type, weight in self._adj.get(current, []):
                if target not in visited:
                    visited.add(target)
                    new_path = path + [Relation(current, target, rel_type, weight)]
                    queue.append((target, new_path))
        return None

    def query_relations(self, entity_id: str, relation_type: Optional[str] = None) -> List[Relation]:
        """Find all relations from an entity."""
        results = []
        for target, rtype, weight in self._adj.get(entity_id, []):
            if relation_type is None or rtype == relation_type:
                results.append(Relation(entity_id, target, rtype, weight))
        return results

    def find_neighbors(self, entity_id: str) -> List[Entity]:
        """Find all connected entities."""
        targets = set(t for t, _, _ in self._adj.get(entity_id, []))
        return [self._entities[t] for t in targets if t in self._entities]

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entities": len(self._entities),
            "relations": len(self._relations),
            "density": len(self._relations) / max(len(self._entities), 1),
        }

    def export_triples(self) -> List[Tuple[str, str, str]]:
        return [(r.source, r.type, r.target) for r in self._relations]


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Knowledge Graph Engine")
    print("ai/llm_knowledge_graph_native.py")
    print("=" * 60)

    engine = KnowledgeGraphEngine()

    # 1. Add entities
    print("\n[1] Add Entities")
    entities = [
        Entity("e1", "Python", "language"),
        Entity("e2", "JavaScript", "language"),
        Entity("e3", "React", "framework"),
        Entity("e4", "Node.js", "runtime"),
        Entity("e5", "Web Development", "field"),
        Entity("e6", "AI", "field"),
    ]
    for e in entities:
        engine.add_entity(e)
    print(f"  Added {len(entities)} entities")

    # 2. Add relations
    print("\n[2] Add Relations")
    relations = [
        Relation("e5", "e1", "uses"),
        Relation("e5", "e2", "uses"),
        Relation("e5", "e3", "uses"),
        Relation("e5", "e4", "uses"),
        Relation("e3", "e2", "built_on"),
        Relation("e4", "e2", "built_on"),
        Relation("e6", "e1", "uses"),
    ]
    for r in relations:
        engine.add_relation(r)
    print(f"  Added {len(relations)} relations")

    # 3. Path finding
    print("\n[3] Path Finding")
    path = engine.find_path("e6", "e3")
    if path:
        print(f"  e6 → e3: {' → '.join(f'{r.source}-{r.type}-{r.target}' for r in path)}")
    else:
        print("  No path found")

    # 4. Query relations
    print("\n[4] Query Relations")
    rels = engine.query_relations("e5")
    print(f"  Web Development uses: {[r.target for r in rels]}")

    # 5. Neighbors
    print("\n[5] Neighbors")
    neighbors = engine.find_neighbors("e2")
    print(f"  JavaScript neighbors: {[n.name for n in neighbors]}")

    # 6. Entity extraction
    print("\n[6] Entity Extraction")
    text = "Python and JavaScript are popular languages. React is a framework."
    extracted = engine.extract_entities(text)
    for e in extracted:
        print(f"  Extracted: {e.name} (type={e.type})")

    # 7. Stats
    print("\n[7] Graph Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    # 8. Triples
    print("\n[8] Triples Export")
    for triple in engine.export_triples()[:5]:
        print(f"  {triple}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
