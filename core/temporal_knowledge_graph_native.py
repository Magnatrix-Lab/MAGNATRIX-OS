
"""
temporal_knowledge_graph_native.py
MAGNATRIX-OS — Temporal Knowledge Graph

Inspired by Synapse (ardhaecosystem/synapse):
Temporal knowledge graph memory that knows WHEN facts were true,
not just THAT they were true. Query the past, not just the present.

Pure Python standard library.
"""

import json
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import hashlib


@dataclass
class TemporalFact:
    """A fact that existed at a specific point in time."""
    fact_id: str
    subject: str
    predicate: str
    object: str
    valid_from: str
    valid_until: Optional[str] = None
    confidence: float = 1.0
    source: str = ""
    context: str = ""

    def is_valid_at(self, timestamp: str) -> bool:
        t = datetime.fromisoformat(timestamp)
        from_t = datetime.fromisoformat(self.valid_from)
        if t < from_t:
            return False
        if self.valid_until:
            until_t = datetime.fromisoformat(self.valid_until)
            return t <= until_t
        return True


@dataclass
class TemporalEdge:
    """Relationship between entities with temporal validity."""
    edge_id: str
    from_entity: str
    to_entity: str
    relation: str
    valid_from: str
    valid_until: Optional[str] = None
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


class TemporalKnowledgeGraph:
    """Time-aware knowledge graph with historical querying."""

    def __init__(self, graph_file: str = "temporal_graph.json"):
        self.graph_file = Path(graph_file)
        self.facts: Dict[str, TemporalFact] = {}
        self.edges: Dict[str, TemporalEdge] = {}
        self.entities: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if self.graph_file.exists():
            with open(self.graph_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for fid, fd in data.get("facts", {}).items():
                    self.facts[fid] = TemporalFact(**fd)
                for eid, ed in data.get("edges", {}).items():
                    self.edges[eid] = TemporalEdge(**ed)
                self.entities = set(data.get("entities", []))

    def _save(self) -> None:
        self.graph_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "facts": {fid: asdict(f) for fid, f in self.facts.items()},
            "edges": {eid: asdict(e) for eid, e in self.edges.items()},
            "entities": list(self.entities),
            "updated": datetime.now().isoformat(),
        }
        with open(self.graph_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _generate_id(self, subject: str, predicate: str, obj: str, timestamp: str) -> str:
        content = f"{subject}:{predicate}:{obj}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def add_fact(self, subject: str, predicate: str, obj: str,
                 confidence: float = 1.0, source: str = "", context: str = "") -> TemporalFact:
        timestamp = datetime.now().isoformat()
        fact_id = self._generate_id(subject, predicate, obj, timestamp)
        # Check if existing fact needs updating
        for fid, existing in self.facts.items():
            if existing.subject == subject and existing.predicate == predicate and existing.object == obj:
                if existing.valid_until is None:
                    # Same fact still valid, just update confidence
                    existing.confidence = max(existing.confidence, confidence)
                    self._save()
                    return existing
        # Create new fact
        fact = TemporalFact(
            fact_id=fact_id, subject=subject, predicate=predicate, object=obj,
            valid_from=timestamp, confidence=confidence, source=source, context=context,
        )
        self.facts[fact_id] = fact
        self.entities.add(subject)
        self.entities.add(obj)
        self._save()
        return fact

    def invalidate_fact(self, fact_id: str) -> bool:
        if fact_id in self.facts:
            self.facts[fact_id].valid_until = datetime.now().isoformat()
            self._save()
            return True
        return False

    def add_edge(self, from_entity: str, to_entity: str, relation: str,
                 weight: float = 1.0, properties: Optional[Dict] = None) -> TemporalEdge:
        timestamp = datetime.now().isoformat()
        edge_id = self._generate_id(from_entity, relation, to_entity, timestamp)
        edge = TemporalEdge(
            edge_id=edge_id, from_entity=from_entity, to_entity=to_entity,
            relation=relation, valid_from=timestamp, weight=weight,
            properties=properties or {},
        )
        self.edges[edge_id] = edge
        self.entities.add(from_entity)
        self.entities.add(to_entity)
        self._save()
        return edge

    def query(self, subject: Optional[str] = None, predicate: Optional[str] = None,
              obj: Optional[str] = None, timestamp: Optional[str] = None) -> List[TemporalFact]:
        """Query facts, optionally at a specific time."""
        ts = timestamp or datetime.now().isoformat()
        results = []
        for fact in self.facts.values():
            if subject and fact.subject != subject:
                continue
            if predicate and fact.predicate != predicate:
                continue
            if obj and fact.object != obj:
                continue
            if fact.is_valid_at(ts):
                results.append(fact)
        return sorted(results, key=lambda f: f.valid_from, reverse=True)

    def what_was_true(self, timestamp: str) -> List[TemporalFact]:
        """Query all facts that were true at a given time."""
        return [f for f in self.facts.values() if f.is_valid_at(timestamp)]

    def get_entity_history(self, entity: str) -> List[TemporalFact]:
        """Get all facts about an entity over time."""
        return sorted(
            [f for f in self.facts.values() if f.subject == entity or f.object == entity],
            key=lambda f: f.valid_from,
        )

    def get_neighbors(self, entity: str, timestamp: Optional[str] = None) -> List[Dict]:
        """Get connected entities."""
        ts = timestamp or datetime.now().isoformat()
        neighbors = []
        for edge in self.edges.values():
            if edge.from_entity == entity or edge.to_entity == entity:
                if edge.valid_until is None or datetime.fromisoformat(ts) <= datetime.fromisoformat(edge.valid_until):
                    other = edge.to_entity if edge.from_entity == entity else edge.from_entity
                    neighbors.append({"entity": other, "relation": edge.relation, "weight": edge.weight})
        return neighbors

    def to_dict(self) -> Dict:
        return {
            "facts": len(self.facts),
            "edges": len(self.edges),
            "entities": len(self.entities),
        }


__all__ = ["TemporalKnowledgeGraph", "TemporalFact", "TemporalEdge"]
