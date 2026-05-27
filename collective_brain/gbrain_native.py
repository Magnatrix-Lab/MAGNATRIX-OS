#!/usr/bin/env python3
"""
gbrain_native.py — Native reimplementation of garrytan/gbrain.
Knowledge graph engine, semantic memory, reasoning patterns, memory palace,
spaced repetition, and insight generation. Pure Python, no hard dependencies.
"""

from __future__ import annotations

import math
import json
import sqlite3
import hashlib
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — BrainCore: Knowledge Graph Engine & Semantic Memory
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ConceptNode:
    """A concept node in the knowledge graph."""
    id: str
    label: str
    category: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0
    activation: float = 0.0  # current activation level (decays over time)
    visit_count: int = 0

    def __repr__(self) -> str:
        return f"<ConceptNode id={self.id} label={self.label} cat={self.category}>"

    def activate(self, amount: float = 1.0) -> None:
        """Activate this node (spread activation)."""
        self.activation = min(1.0, self.activation + amount)
        self.visit_count += 1

    def decay(self, rate: float = 0.1) -> None:
        """Decay activation over time."""
        self.activation = max(0.0, self.activation - rate)


@dataclass
class RelationEdge:
    """A typed relation between two concept nodes."""
    id: str
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0
    bidirectional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        arrow = "<->" if self.bidirectional else "->"
        return f"<RelationEdge {self.source_id} {arrow} {self.target_id} ({self.relation_type})>"


class SemanticMemory:
    """In-memory semantic memory store with SQLite persistence option."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._nodes: Dict[str, ConceptNode] = {}
        self._edges: Dict[str, RelationEdge] = {}
        self._adjacency: Dict[str, List[str]] = {}  # node_id -> list of edge_ids
        self._db_path = db_path
        if db_path:
            self._init_db()

    def __repr__(self) -> str:
        return f"<SemanticMemory nodes={len(self._nodes)} edges={len(self._edges)}>"

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                category TEXT,
                description TEXT,
                metadata TEXT,
                embedding TEXT,
                created_at TEXT,
                confidence REAL,
                activation REAL,
                visit_count INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                source_id TEXT,
                target_id TEXT,
                relation_type TEXT,
                weight REAL,
                bidirectional INTEGER,
                metadata TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def add_node(self, node: ConceptNode) -> None:
        """Add a concept node to memory."""
        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []
        if self._db_path:
            self._persist_node(node)

    def _persist_node(self, node: ConceptNode) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """INSERT OR REPLACE INTO concepts VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (node.id, node.label, node.category, node.description,
             json.dumps(node.metadata), json.dumps(node.embedding),
             node.created_at.isoformat(), node.confidence, node.activation, node.visit_count)
        )
        conn.commit()
        conn.close()

    def add_edge(self, edge: RelationEdge) -> None:
        """Add a relation edge between two nodes."""
        self._edges[edge.id] = edge
        self._adjacency.setdefault(edge.source_id, []).append(edge.id)
        if edge.bidirectional:
            self._adjacency.setdefault(edge.target_id, []).append(edge.id)
        if self._db_path:
            self._persist_edge(edge)

    def _persist_edge(self, edge: RelationEdge) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """INSERT OR REPLACE INTO relations VALUES (?,?,?,?,?,?,?,?)""",
            (edge.id, edge.source_id, edge.target_id, edge.relation_type,
             edge.weight, int(edge.bidirectional), json.dumps(edge.metadata),
             edge.created_at.isoformat())
        )
        conn.commit()
        conn.close()

    def get_node(self, node_id: str) -> Optional[ConceptNode]:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[RelationEdge]:
        return self._edges.get(edge_id)

    def neighbors(self, node_id: str) -> List[ConceptNode]:
        """Get all neighboring nodes connected by edges."""
        result: List[ConceptNode] = []
        for edge_id in self._adjacency.get(node_id, []):
            edge = self._edges.get(edge_id)
            if edge:
                other = edge.target_id if edge.source_id == node_id else edge.source_id
                node = self._nodes.get(other)
                if node:
                    result.append(node)
        return result

    def search(self, query: str, top_k: int = 5) -> List[ConceptNode]:
        """Simple keyword search over node labels and descriptions."""
        query_lower = query.lower()
        scored: List[Tuple[float, ConceptNode]] = []
        for node in self._nodes.values():
            score = 0.0
            if query_lower in node.label.lower():
                score += 2.0
            if query_lower in node.description.lower():
                score += 1.0
            if query_lower in node.category.lower():
                score += 0.5
            if score > 0:
                scored.append((score, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in scored[:top_k]]

    def similarity(self, node_a: ConceptNode, node_b: ConceptNode) -> float:
        """Cosine similarity between two node embeddings (if available)."""
        if not node_a.embedding or not node_b.embedding:
            return 0.0
        emb_a = node_a.embedding
        emb_b = node_b.embedding
        dot = sum(a * b for a, b in zip(emb_a, emb_b))
        norm_a = math.sqrt(sum(x * x for x in emb_a))
        norm_b = math.sqrt(sum(x * x for x in emb_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def spread_activation(self, start_id: str, depth: int = 2, decay: float = 0.5) -> Dict[str, float]:
        """Spreading activation from a starting node. Returns node_id -> activation."""
        activations: Dict[str, float] = {start_id: 1.0}
        current_layer = {start_id}
        for _ in range(depth):
            next_layer: Set[str] = set()
            for node_id in current_layer:
                for edge_id in self._adjacency.get(node_id, []):
                    edge = self._edges.get(edge_id)
                    if not edge:
                        continue
                    other = edge.target_id if edge.source_id == node_id else edge.source_id
                    if other not in activations:
                        activations[other] = 0.0
                    activations[other] += activations[node_id] * edge.weight * decay
                    next_layer.add(other)
            current_layer = next_layer
        return activations

    def all_nodes(self) -> List[ConceptNode]:
        return list(self._nodes.values())

    def all_edges(self) -> List[RelationEdge]:
        return list(self._edges.values())


class KnowledgeGraph:
    """High-level knowledge graph with graph traversal and analytics."""

    def __init__(self, memory: Optional[SemanticMemory] = None) -> None:
        self.memory = memory or SemanticMemory()

    def __repr__(self) -> str:
        return f"<KnowledgeGraph nodes={len(self.memory.all_nodes())} edges={len(self.memory.all_edges())}>"

    def add_concept(self, label: str, category: str, description: str = "",
                    metadata: Optional[Dict[str, Any]] = None) -> ConceptNode:
        node_id = hashlib.sha256(f"{label}:{category}".encode()).hexdigest()[:16]
        node = ConceptNode(
            id=node_id, label=label, category=category,
            description=description, metadata=metadata or {}
        )
        self.memory.add_node(node)
        return node

    def relate(self, source: ConceptNode, target: ConceptNode,
               relation_type: str, weight: float = 1.0,
               bidirectional: bool = False) -> RelationEdge:
        edge_id = hashlib.sha256(
            f"{source.id}:{target.id}:{relation_type}".encode()
        ).hexdigest()[:16]
        edge = RelationEdge(
            id=edge_id, source_id=source.id, target_id=target.id,
            relation_type=relation_type, weight=weight,
            bidirectional=bidirectional
        )
        self.memory.add_edge(edge)
        return edge

    def path_between(self, start_id: str, end_id: str,
                     max_depth: int = 5) -> Optional[List[RelationEdge]]:
        """BFS to find shortest path between two nodes."""
        if start_id == end_id:
            return []
        queue: List[Tuple[str, List[RelationEdge]]] = [(start_id, [])]
        visited: Set[str] = {start_id}
        while queue:
            current_id, path = queue.pop(0)
            if len(path) >= max_depth:
                continue
            for edge_id in self.memory._adjacency.get(current_id, []):
                edge = self.memory._edges.get(edge_id)
                if not edge:
                    continue
                other = edge.target_id if edge.source_id == current_id else edge.source_id
                if other == end_id:
                    return path + [edge]
                if other not in visited:
                    visited.add(other)
                    queue.append((other, path + [edge]))
        return None

    def connected_components(self) -> List[List[str]]:
        """Find all connected components in the graph."""
        visited: Set[str] = set()
        components: List[List[str]] = []
        for node_id in self.memory._nodes:
            if node_id not in visited:
                component: List[str] = []
                stack = [node_id]
                while stack:
                    curr = stack.pop()
                    if curr in visited:
                        continue
                    visited.add(curr)
                    component.append(curr)
                    for edge_id in self.memory._adjacency.get(curr, []):
                        edge = self.memory._edges.get(edge_id)
                        if edge:
                            other = edge.target_id if edge.source_id == curr else edge.source_id
                            if other not in visited:
                                stack.append(other)
                components.append(component)
        return components

    def centrality(self, node_id: str) -> float:
        """Simple degree centrality (normalized)."""
        if not self.memory._nodes:
            return 0.0
        degree = len(self.memory._adjacency.get(node_id, []))
        max_degree = max(len(v) for v in self.memory._adjacency.values()) if self.memory._adjacency else 1
        return degree / max_degree


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ThoughtEngine: Reasoning Patterns
# ═══════════════════════════════════════════════════════════════════════════════


class Reasoner(ABC):
    """Abstract base for all reasoning engines."""

    @abstractmethod
    def reason(self, premises: List[Any]) -> Any:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class DeductiveReasoner(Reasoner):
    """
    Deductive reasoning: if all premises are true, conclusion must be true.
    Implements simple syllogistic pattern matching.
    """

    def reason(self, premises: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        premises: list of {subject, predicate, object} dicts.
        Returns inferred conclusions.
        """
        conclusions: List[Dict[str, Any]] = []
        # Simple transitivity: A->B, B->C => A->C
        for i, p1 in enumerate(premises):
            for p2 in premises[i+1:]:
                if p1.get("object") == p2.get("subject"):
                    conclusions.append({
                        "subject": p1["subject"],
                        "predicate": p2["predicate"],
                        "object": p2["object"],
                        "inference_type": "transitivity",
                        "certainty": min(p1.get("certainty", 1.0), p2.get("certainty", 1.0))
                    })
        return conclusions


class InductiveReasoner(Reasoner):
    """
    Inductive reasoning: generalize from specific observations.
    Finds patterns in observations and proposes general rules.
    """

    def reason(self, premises: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        premises: list of observations {instance, property, value}.
        Returns generalizations.
        """
        conclusions: List[Dict[str, Any]] = []
        # Group by property
        by_property: Dict[str, List[Any]] = {}
        for obs in premises:
            prop = obs.get("property")
            by_property.setdefault(prop, []).append(obs)

        for prop, obs_list in by_property.items():
            values = [o.get("value") for o in obs_list if o.get("value") is not None]
            if not values:
                continue
            if all(isinstance(v, (int, float)) for v in values):
                # Numeric: compute mean/stdev and generalize
                if len(values) >= 2:
                    mean_val = statistics.mean(values)
                    stdev_val = statistics.stdev(values) if len(values) > 1 else 0
                    conclusions.append({
                        "generalization_type": "numeric_trend",
                        "property": prop,
                        "mean": mean_val,
                        "stdev": stdev_val,
                        "sample_size": len(values),
                        "inference": f"Instances of '{prop}' tend toward {mean_val:.2f}"
                    })
            else:
                # Categorical: find most common value
                counts: Dict[Any, int] = {}
                for v in values:
                    counts[v] = counts.get(v, 0) + 1
                most_common = max(counts, key=counts.get)
                freq = counts[most_common] / len(values)
                if freq >= 0.5:
                    conclusions.append({
                        "generalization_type": "categorical_majority",
                        "property": prop,
                        "most_common": most_common,
                        "frequency": freq,
                        "sample_size": len(values),
                        "inference": f"Most instances have '{prop}' = '{most_common}'"
                    })
        return conclusions


class AnalogicalReasoner(Reasoner):
    """
    Analogical reasoning: map similarities between two domains.
    Finds structural correspondences.
    """

    def reason(self, premises: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        premises: {source_domain, target_domain, source_relations, target_relations}.
        Returns analogical mappings.
        """
        conclusions: List[Dict[str, Any]] = []
        if len(premises) < 1:
            return conclusions
        for premise in premises:
            source_rels = premise.get("source_relations", [])
            target_rels = premise.get("target_relations", [])
            mappings: List[Dict[str, str]] = []
            for s_rel in source_rels:
                for t_rel in target_rels:
                    if s_rel.get("relation_type") == t_rel.get("relation_type"):
                        mappings.append({
                            "source": s_rel.get("subject"),
                            "target": t_rel.get("subject"),
                            "relation": s_rel.get("relation_type")
                        })
            if mappings:
                conclusions.append({
                    "source_domain": premise.get("source_domain"),
                    "target_domain": premise.get("target_domain"),
                    "mappings": mappings,
                    "inference": f"Mapped {len(mappings)} relations from {premise.get('source_domain')} to {premise.get('target_domain')}"
                })
        return conclusions


class CausalInferencer(Reasoner):
    """
    Causal inference: identify cause-effect relationships.
    Uses temporal precedence and co-occurrence heuristics.
    """

    def reason(self, premises: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        premises: list of events {event, timestamp, outcome}.
        Returns candidate causal links.
        """
        conclusions: List[Dict[str, Any]] = []
        # Sort by time
        sorted_events = sorted(premises, key=lambda x: x.get("timestamp", datetime.min))
        for i, event in enumerate(sorted_events):
            if i == 0:
                continue
            prev = sorted_events[i - 1]
            time_diff = event.get("timestamp", datetime.min) - prev.get("timestamp", datetime.min)
            if time_diff.total_seconds() <= 3600:  # within 1 hour
                conclusions.append({
                    "cause": prev.get("event"),
                    "effect": event.get("event"),
                    "time_gap_seconds": time_diff.total_seconds(),
                    "inference_type": "temporal_proximity",
                    "confidence": 0.6  # heuristic baseline
                })
        return conclusions


class ThoughtEngine:
    """Orchestrates multiple reasoning patterns on a knowledge graph."""

    def __init__(self, knowledge_graph: KnowledgeGraph) -> None:
        self.kg = knowledge_graph
        self.deductive = DeductiveReasoner()
        self.inductive = InductiveReasoner()
        self.analogical = AnalogicalReasoner()
        self.causal = CausalInferencer()

    def __repr__(self) -> str:
        return f"<ThoughtEngine reasoners=4>"

    def reason_about(self, node_id: str, mode: str = "deductive") -> List[Dict[str, Any]]:
        """Apply a reasoning mode to a node's neighborhood."""
        node = self.kg.memory.get_node(node_id)
        if not node:
            return []
        neighbors = self.kg.memory.neighbors(node_id)
        premises: List[Dict[str, Any]] = []
        for n in neighbors:
            premises.append({
                "subject": node.label,
                "predicate": "related_to",
                "object": n.label,
                "certainty": node.confidence
            })
        if mode == "deductive":
            return self.deductive.reason(premises)
        elif mode == "inductive":
            return self.inductive.reason(premises)
        elif mode == "analogical":
            return self.analogical.reason([{
                "source_domain": node.category,
                "target_domain": "general",
                "source_relations": premises,
                "target_relations": premises
            }])
        elif mode == "causal":
            return self.causal.reason([{
                "event": node.label,
                "timestamp": node.created_at,
                "outcome": n.label
            } for n in neighbors])
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — MemoryPalace: Spatial Memory Organization
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Locus:
    """A single memory location (locus) in the Memory Palace."""
    id: str
    name: str
    description: str
    coordinates: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    concept_ids: List[str] = field(default_factory=list)
    image_anchor: str = ""  # mental image to anchor memory
    color_tag: str = "#3498db"

    def __repr__(self) -> str:
        return f"<Locus {self.name} concepts={len(self.concept_ids)}>"


@dataclass
class Room:
    """A room in the Memory Palace containing multiple loci."""
    id: str
    name: str
    theme: str = "general"
    loci: Dict[str, Locus] = field(default_factory=dict)
    connections: List[str] = field(default_factory=list)  # connected room_ids

    def __repr__(self) -> str:
        return f"<Room {self.name} loci={len(self.loci)}>"

    def add_locus(self, locus: Locus) -> None:
        self.loci[locus.id] = locus

    def get_locus(self, locus_id: str) -> Optional[Locus]:
        return self.loci.get(locus_id)


class MemoryPalace:
    """
    Digital implementation of the Method of Loci (Memory Palace).
    Organizes knowledge spatially for enhanced recall.
    """

    def __init__(self, name: str = "Default Palace") -> None:
        self.name = name
        self._rooms: Dict[str, Room] = {}
        self._concept_to_locus: Dict[str, str] = {}  # concept_id -> locus_id

    def __repr__(self) -> str:
        total_loci = sum(len(r.loci) for r in self._rooms.values())
        return f"<MemoryPalace '{self.name}' rooms={len(self._rooms)} loci={total_loci}>"

    def create_room(self, room_name: str, theme: str = "general") -> Room:
        room_id = hashlib.sha256(room_name.encode()).hexdigest()[:12]
        room = Room(id=room_id, name=room_name, theme=theme)
        self._rooms[room_id] = room
        return room

    def add_locus(self, room_id: str, locus: Locus) -> None:
        room = self._rooms.get(room_id)
        if room:
            room.add_locus(locus)
            for cid in locus.concept_ids:
                self._concept_to_locus[cid] = locus.id

    def place_concept(self, room_id: str, locus_id: str, concept_id: str) -> bool:
        """Place a concept at a specific locus."""
        room = self._rooms.get(room_id)
        if not room:
            return False
        locus = room.get_locus(locus_id)
        if not locus:
            return False
        if concept_id not in locus.concept_ids:
            locus.concept_ids.append(concept_id)
        self._concept_to_locus[concept_id] = locus_id
        return True

    def find_concept(self, concept_id: str) -> Optional[Tuple[str, str]]:
        """Find which room and locus contains a concept."""
        locus_id = self._concept_to_locus.get(concept_id)
        if not locus_id:
            return None
        for room_id, room in self._rooms.items():
            if locus_id in room.loci:
                return (room_id, locus_id)
        return None

    def walk_path(self, start_room_id: str) -> List[Dict[str, Any]]:
        """Return a traversal path through all rooms (DFS)."""
        path: List[Dict[str, Any]] = []
        visited: Set[str] = set()
        stack = [start_room_id]
        while stack:
            room_id = stack.pop()
            if room_id in visited:
                continue
            visited.add(room_id)
            room = self._rooms.get(room_id)
            if room:
                path.append({
                    "room": room.name,
                    "loci": [l.name for l in room.loci.values()],
                    "theme": room.theme
                })
                for conn in room.connections:
                    if conn not in visited:
                        stack.append(conn)
        return path

    def connect_rooms(self, room_a_id: str, room_b_id: str) -> None:
        """Create a passage between two rooms."""
        room_a = self._rooms.get(room_a_id)
        room_b = self._rooms.get(room_b_id)
        if room_a and room_b:
            if room_b_id not in room_a.connections:
                room_a.connections.append(room_b_id)
            if room_a_id not in room_b.connections:
                room_b.connections.append(room_a_id)

    def all_rooms(self) -> List[Room]:
        return list(self._rooms.values())


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — LearningModule: Spaced Repetition & Forgetting Curve
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ReviewItem:
    """An item scheduled for spaced repetition review."""
    id: str
    concept_id: str
    interval_days: float = 1.0
    ease_factor: float = 2.5
    repetitions: int = 0
    last_review: Optional[datetime] = None
    next_review: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lapses: int = 0

    def __repr__(self) -> str:
        return f"<ReviewItem concept={self.concept_id} interval={self.interval_days:.1f}d reps={self.repetitions}>"


class ForgettingCurve:
    """
    Models Ebbinghaus forgetting curve: R = e^(-t/S)
    where R = retention, t = time since learning, S = stability.
    """

    def __init__(self, base_stability_hours: float = 24.0) -> None:
        self.base_stability = base_stability_hours

    def __repr__(self) -> str:
        return f"<ForgettingCurve base_stability={self.base_stability}h>"

    def retention(self, hours_elapsed: float, repetitions: int = 0) -> float:
        """Probability of recall after elapsed hours."""
        stability = self.base_stability * (1 + repetitions * 0.5)
        return math.exp(-hours_elapsed / stability)

    def optimal_review_time(self, repetitions: int = 0) -> float:
        """Return hours until optimal review (retention ~0.85)."""
        stability = self.base_stability * (1 + repetitions * 0.5)
        return -stability * math.log(0.85)


class SpacedRepetition:
    """
    SM-2 inspired spaced repetition scheduler.
    Manages review intervals based on performance ratings (0-5).
    """

    def __init__(self) -> None:
        self._items: Dict[str, ReviewItem] = {}
        self._curve = ForgettingCurve()

    def __repr__(self) -> str:
        return f"<SpacedRepetition items={len(self._items)}>"

    def add_item(self, concept_id: str) -> ReviewItem:
        item_id = hashlib.sha256(f"sr:{concept_id}".encode()).hexdigest()[:12]
        item = ReviewItem(id=item_id, concept_id=concept_id)
        self._items[item_id] = item
        return item

    def get_item(self, concept_id: str) -> Optional[ReviewItem]:
        for item in self._items.values():
            if item.concept_id == concept_id:
                return item
        return None

    def rate_performance(self, concept_id: str, rating: int) -> ReviewItem:
        """
        Rate recall performance (0-5):
        0 = complete blackout, 1 = incorrect but recognized, 2 = incorrect but easy,
        3 = correct with difficulty, 4 = correct, 5 = perfect.
        """
        item = self.get_item(concept_id)
        if not item:
            item = self.add_item(concept_id)
        now = datetime.now(timezone.utc)
        if rating < 3:
            item.lapses += 1
            item.repetitions = 0
            item.interval_days = 1.0
            item.ease_factor = max(1.3, item.ease_factor - 0.2)
        else:
            if item.repetitions == 0:
                item.interval_days = 1.0
            elif item.repetitions == 1:
                item.interval_days = 6.0
            else:
                item.interval_days *= item.ease_factor
            item.repetitions += 1
            item.ease_factor += 0.1 - (5 - rating) * 0.08
            item.ease_factor = max(1.3, item.ease_factor)
        item.last_review = now
        item.next_review = now + timedelta(days=item.interval_days)
        return item

    def due_items(self, before: Optional[datetime] = None) -> List[ReviewItem]:
        """Get all items due for review."""
        cutoff = before or datetime.now(timezone.utc)
        return [item for item in self._items.values() if item.next_review <= cutoff]

    def predict_retention(self, concept_id: str) -> float:
        """Predict current retention probability."""
        item = self.get_item(concept_id)
        if not item or not item.last_review:
            return 0.0
        elapsed = (datetime.now(timezone.utc) - item.last_review).total_seconds() / 3600
        return self._curve.retention(elapsed, item.repetitions)

    def stats(self) -> Dict[str, Any]:
        """Return learning statistics."""
        total = len(self._items)
        due = len(self.due_items())
        avg_interval = statistics.mean([i.interval_days for i in self._items.values()]) if self._items else 0
        avg_ease = statistics.mean([i.ease_factor for i in self._items.values()]) if self._items else 0
        return {
            "total_items": total,
            "due_now": due,
            "average_interval_days": round(avg_interval, 2),
            "average_ease_factor": round(avg_ease, 2)
        }


class ReviewScheduler:
    """Daily review scheduler with session planning."""

    def __init__(self, sr: SpacedRepetition) -> None:
        self.sr = sr
        self._daily_limit: int = 50
        self._session_duration_minutes: int = 20

    def __repr__(self) -> str:
        return f"<ReviewScheduler limit={self._daily_limit} session={self._session_duration_minutes}min>"

    def set_limits(self, daily_limit: int, session_minutes: int) -> None:
        self._daily_limit = daily_limit
        self._session_duration_minutes = session_minutes

    def today_plan(self) -> Dict[str, Any]:
        due = self.sr.due_items()
        selected = due[:self._daily_limit]
        return {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "total_due": len(due),
            "selected_for_review": len(selected),
            "estimated_minutes": len(selected) * 2,  # ~2 min per item
            "items": [item.concept_id for item in selected]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — InsightGenerator: Pattern Recognition & Cross-Domain Analogy
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Insight:
    """A generated insight with confidence and supporting evidence."""
    id: str
    title: str
    description: str
    confidence: float
    source_concepts: List[str] = field(default_factory=list)
    insight_type: str = "pattern"
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Insight {self.title} confidence={self.confidence:.2f}>"


class PatternRecognizer:
    """Recognizes recurring patterns across knowledge nodes."""

    def __init__(self, knowledge_graph: KnowledgeGraph) -> None:
        self.kg = knowledge_graph

    def __repr__(self) -> str:
        return f"<PatternRecognizer>"

    def find_clusters(self, min_size: int = 3) -> List[List[str]]:
        """Find clusters of densely connected nodes."""
        components = self.kg.connected_components()
        return [c for c in components if len(c) >= min_size]

    def find_bridges(self) -> List[Tuple[str, str]]:
        """Find edges that connect different clusters (bridging concepts)."""
        bridges: List[Tuple[str, str]] = []
        for edge in self.kg.memory.all_edges():
            # Check if removing this edge increases component count
            # Simplified: edges with low centrality endpoints are potential bridges
            src_centrality = self.kg.centrality(edge.source_id)
            tgt_centrality = self.kg.centrality(edge.target_id)
            if src_centrality < 0.3 and tgt_centrality < 0.3:
                bridges.append((edge.source_id, edge.target_id))
        return bridges

    def frequent_subgraphs(self, size: int = 3) -> List[Dict[str, Any]]:
        """Find frequently occurring small subgraph patterns."""
        patterns: Dict[str, int] = {}
        for node_id in self.kg.memory._nodes:
            neighbors = self.kg.memory.neighbors(node_id)
            if len(neighbors) >= size - 1:
                pattern_key = f"star:{len(neighbors)}"
                patterns[pattern_key] = patterns.get(pattern_key, 0) + 1
        return [{"pattern": k, "frequency": v} for k, v in sorted(patterns.items(), key=lambda x: -x[1])[:5]]


class CrossDomainAnalogy:
    """Generates analogies between different knowledge domains."""

    def __init__(self, knowledge_graph: KnowledgeGraph) -> None:
        self.kg = knowledge_graph

    def __repr__(self) -> str:
        return f"<CrossDomainAnalogy>"

    def find_analogies(self, source_domain: str, target_domain: str,
                       top_k: int = 3) -> List[Dict[str, Any]]:
        """Find structural analogies between two domains."""
        source_nodes = [n for n in self.kg.memory.all_nodes() if n.category == source_domain]
        target_nodes = [n for n in self.kg.memory.all_nodes() if n.category == target_domain]
        analogies: List[Dict[str, Any]] = []
        for sn in source_nodes:
            for tn in target_nodes:
                sim = self.kg.memory.similarity(sn, tn)
                if sim > 0.5:
                    analogies.append({
                        "source": sn.label,
                        "target": tn.label,
                        "similarity": sim,
                        "analogy": f"{sn.label} in {source_domain} is like {tn.label} in {target_domain}"
                    })
        analogies.sort(key=lambda x: x["similarity"], reverse=True)
        return analogies[:top_k]

    def transfer_knowledge(self, source_concept_id: str, target_domain: str) -> List[Insight]:
        """Transfer properties from a source concept to a target domain."""
        source = self.kg.memory.get_node(source_concept_id)
        if not source:
            return []
        target_nodes = [n for n in self.kg.memory.all_nodes() if n.category == target_domain]
        insights: List[Insight] = []
        for tn in target_nodes:
            insight_id = hashlib.sha256(f"transfer:{source.id}:{tn.id}".encode()).hexdigest()[:12]
            insights.append(Insight(
                id=insight_id,
                title=f"Knowledge Transfer: {source.label} -> {tn.label}",
                description=f"Properties from {source.label} may apply to {tn.label}",
                confidence=0.5,
                source_concepts=[source.id, tn.id],
                insight_type="knowledge_transfer"
            ))
        return insights


class InsightGenerator:
    """Orchestrates pattern recognition and cross-domain analogy to generate insights."""

    def __init__(self, knowledge_graph: KnowledgeGraph) -> None:
        self.kg = knowledge_graph
        self.pattern_recognizer = PatternRecognizer(knowledge_graph)
        self.analogy_engine = CrossDomainAnalogy(knowledge_graph)
        self._insights: List[Insight] = []

    def __repr__(self) -> str:
        return f"<InsightGenerator insights_generated={len(self._insights)}>"

    def generate(self, focus_domain: Optional[str] = None) -> List[Insight]:
        """Generate insights from the current knowledge graph state."""
        new_insights: List[Insight] = []
        # Pattern insights
        clusters = self.pattern_recognizer.find_clusters(min_size=3)
        for cluster in clusters[:3]:
            nodes = [self.kg.memory.get_node(nid) for nid in cluster]
            labels = [n.label for n in nodes if n]
            insight_id = hashlib.sha256(f"cluster:{':'.join(cluster)}".encode()).hexdigest()[:12]
            new_insights.append(Insight(
                id=insight_id,
                title=f"Cluster: {labels[0]} et al.",
                description=f"Found densely connected cluster of {len(cluster)} concepts: {', '.join(labels[:5])}",
                confidence=0.7,
                source_concepts=cluster,
                insight_type="cluster"
            ))
        # Bridge insights
        bridges = self.pattern_recognizer.find_bridges()[:3]
        for src_id, tgt_id in bridges:
            src = self.kg.memory.get_node(src_id)
            tgt = self.kg.memory.get_node(tgt_id)
            if src and tgt:
                insight_id = hashlib.sha256(f"bridge:{src_id}:{tgt_id}".encode()).hexdigest()[:12]
                new_insights.append(Insight(
                    id=insight_id,
                    title=f"Bridge: {src.label} <-> {tgt.label}",
                    description=f"These concepts bridge different knowledge regions",
                    confidence=0.6,
                    source_concepts=[src_id, tgt_id],
                    insight_type="bridge"
                ))
        # Domain transfer insights
        domains = list(set(n.category for n in self.kg.memory.all_nodes()))
        if len(domains) >= 2 and focus_domain:
            other = [d for d in domains if d != focus_domain][0]
            transfer_insights = self.analogy_engine.transfer_knowledge(
                [n.id for n in self.kg.memory.all_nodes() if n.category == focus_domain][0], other
            )
            new_insights.extend(transfer_insights[:2])
        self._insights.extend(new_insights)
        return new_insights

    def all_insights(self) -> List[Insight]:
        return self._insights

    def insights_by_type(self, insight_type: str) -> List[Insight]:
        return [i for i in self._insights if i.insight_type == insight_type]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — GBrainKernel: MAGNATRIX Bridge & System Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════


class GBrainKernel:
    """
    Central kernel for gbrain. Bridges to MAGNATRIX layers:
    - Layer 5 (Knowledge / Market Data)
    - Layer 10 (AI Agents / Reasoning)
    """

    def __init__(self, name: str = "gbrain") -> None:
        self.name = name
        self.knowledge_graph = KnowledgeGraph()
        self.thought_engine = ThoughtEngine(self.knowledge_graph)
        self.memory_palace = MemoryPalace(name="Primary Palace")
        self.learning_module = SpacedRepetition()
        self.review_scheduler = ReviewScheduler(self.learning_module)
        self.insight_generator = InsightGenerator(self.knowledge_graph)
        self._hooks: Dict[str, List[Callable[..., Any]]] = {
            "on_learn": [],
            "on_recall": [],
            "on_insight": [],
            "on_review_due": []
        }
        self._initialized_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return (f"<GBrainKernel '{self.name}' nodes={len(self.knowledge_graph.memory.all_nodes())} "
                f"insights={len(self.insight_generator.all_insights())}>")

    def register_hook(self, event: str, callback: Callable[..., Any]) -> None:
        """Register a callback for a system event."""
        if event in self._hooks:
            self._hooks[event].append(callback)

    def _trigger(self, event: str, *args: Any, **kwargs: Any) -> None:
        for cb in self._hooks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception:
                pass

    def learn(self, label: str, category: str, description: str = "",
              metadata: Optional[Dict[str, Any]] = None) -> ConceptNode:
        """Learn a new concept."""
        node = self.knowledge_graph.add_concept(label, category, description, metadata)
        self._trigger("on_learn", node)
        return node

    def relate(self, source_label: str, target_label: str,
               relation_type: str, weight: float = 1.0) -> Optional[RelationEdge]:
        """Create a relation between two concepts by label."""
        source = None
        target = None
        for n in self.knowledge_graph.memory.all_nodes():
            if n.label == source_label:
                source = n
            if n.label == target_label:
                target = n
        if source and target:
            edge = self.knowledge_graph.relate(source, target, relation_type, weight)
            return edge
        return None

    def recall(self, query: str, top_k: int = 5) -> List[ConceptNode]:
        """Recall concepts matching a query."""
        results = self.knowledge_graph.memory.search(query, top_k)
        for node in results:
            node.activate()
            self._trigger("on_recall", node)
        return results

    def reason(self, node_id: str, mode: str = "deductive") -> List[Dict[str, Any]]:
        """Apply reasoning to a concept."""
        return self.thought_engine.reason_about(node_id, mode)

    def schedule_review(self, concept_id: str) -> ReviewItem:
        """Add a concept to the spaced repetition system."""
        return self.learning_module.add_item(concept_id)

    def review(self, concept_id: str, rating: int) -> ReviewItem:
        """Record a review performance rating."""
        item = self.learning_module.rate_performance(concept_id, rating)
        if item.next_review <= datetime.now(timezone.utc):
            self._trigger("on_review_due", item)
        return item

    def generate_insights(self, focus_domain: Optional[str] = None) -> List[Insight]:
        """Generate insights from the knowledge base."""
        insights = self.insight_generator.generate(focus_domain)
        for insight in insights:
            self._trigger("on_insight", insight)
        return insights

    def place_in_palace(self, room_name: str, locus_name: str,
                        concept_id: str) -> bool:
        """Place a concept in the memory palace."""
        room_id = hashlib.sha256(room_name.encode()).hexdigest()[:12]
        room = self.memory_palace._rooms.get(room_id)
        if not room:
            room = self.memory_palace.create_room(room_name)
        locus_id = hashlib.sha256(locus_name.encode()).hexdigest()[:12]
        locus = room.get_locus(locus_id)
        if not locus:
            locus = Locus(id=locus_id, name=locus_name, description="",
                          concept_ids=[])
            self.memory_palace.add_locus(room.id, locus)
        return self.memory_palace.place_concept(room.id, locus_id, concept_id)

    def walk_palace(self, room_name: str) -> List[Dict[str, Any]]:
        """Walk through the memory palace starting from a room."""
        room_id = hashlib.sha256(room_name.encode()).hexdigest()[:12]
        return self.memory_palace.walk_path(room_id)

    def stats(self) -> Dict[str, Any]:
        """Return system-wide statistics."""
        return {
            "kernel_name": self.name,
            "uptime_seconds": (datetime.now(timezone.utc) - self._initialized_at).total_seconds(),
            "concepts": len(self.knowledge_graph.memory.all_nodes()),
            "relations": len(self.knowledge_graph.memory.all_edges()),
            "rooms": len(self.memory_palace.all_rooms()),
            "review_items": len(self.learning_module._items),
            "insights": len(self.insight_generator.all_insights()),
            "due_reviews": len(self.learning_module.due_items())
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO — Full Pipeline
# ═══════════════════════════════════════════════════════════════════════════════


def demo() -> None:
    """Run a full demonstration of the gbrain system."""
    print("=" * 60)
    print("GBRAIN NATIVE — Full System Demo")
    print("=" * 60)

    # 1. Initialize kernel
    brain = GBrainKernel(name="DemoBrain")
    print(f"\n[1] Kernel initialized: {brain}")

    # 2. Learn concepts
    concepts = [
        ("Neural Network", "ai", "Computational model inspired by biological neurons"),
        ("Backpropagation", "ai", "Algorithm for training neural networks via gradient descent"),
        ("Gradient Descent", "ai", "Optimization algorithm for minimizing loss functions"),
        ("Loss Function", "ai", "Function measuring prediction error"),
        ("Synapse", "biology", "Junction between two neurons"),
        ("Neuron", "biology", "Basic unit of the nervous system"),
        ("Action Potential", "biology", "Electrical impulse in neurons"),
        ("Dopamine", "biology", "Neurotransmitter involved in reward and learning"),
        ("Reinforcement Learning", "ai", "Learning via reward and punishment signals"),
        ("Reward Signal", "ai", "Feedback signal indicating success"),
    ]
    nodes: Dict[str, ConceptNode] = {}
    for label, cat, desc in concepts:
        node = brain.learn(label, cat, desc)
        nodes[label] = node
        print(f"  Learned: {node.label} ({node.category})")

    # 3. Create relations
    relations = [
        ("Neural Network", "Backpropagation", "trained_by"),
        ("Backpropagation", "Gradient Descent", "uses"),
        ("Gradient Descent", "Loss Function", "minimizes"),
        ("Neural Network", "Synapse", "analogous_to"),
        ("Neuron", "Action Potential", "produces"),
        ("Synapse", "Dopamine", "releases"),
        ("Reinforcement Learning", "Reward Signal", "depends_on"),
        ("Reward Signal", "Dopamine", "analogous_to"),
    ]
    for src, tgt, rel_type in relations:
        edge = brain.relate(src, tgt, rel_type)
        if edge:
            print(f"  Related: {src} -> {tgt} ({rel_type})")

    # 4. Search and recall
    print("\n[4] Search for 'neuron':")
    results = brain.recall("neuron", top_k=3)
    for r in results:
        print(f"  Found: {r.label} (activation={r.activation:.2f})")

    # 5. Reasoning
    print("\n[5] Deductive reasoning on 'Neural Network':")
    nn_node = nodes["Neural Network"]
    conclusions = brain.reason(nn_node.id, mode="deductive")
    for c in conclusions:
        print(f"  Inferred: {c.get('subject')} -> {c.get('object')} ({c.get('inference_type')})")

    print("\n[5b] Inductive reasoning:")
    inductive_premises = [
        {"property": "accuracy", "value": 0.85},
        {"property": "accuracy", "value": 0.88},
        {"property": "accuracy", "value": 0.82},
        {"property": "speed", "value": "fast"},
        {"property": "speed", "value": "fast"},
    ]
    inductive = InductiveReasoner()
    gen = inductive.reason(inductive_premises)
    for g in gen:
        print(f"  Generalization: {g.get('inference')}")

    # 6. Memory Palace
    print("\n[6] Memory Palace:")
    brain.place_in_palace("AI Room", "Algorithms Shelf", nodes["Backpropagation"].id)
    brain.place_in_palace("AI Room", "Algorithms Shelf", nodes["Gradient Descent"].id)
    brain.place_in_palace("AI Room", "Models Shelf", nodes["Neural Network"].id)
    brain.place_in_palace("Biology Room", "Neurons Shelf", nodes["Neuron"].id)
    brain.place_in_palace("Biology Room", "Neurons Shelf", nodes["Synapse"].id)
    brain.memory_palace.connect_rooms(
        hashlib.sha256("AI Room".encode()).hexdigest()[:12],
        hashlib.sha256("Biology Room".encode()).hexdigest()[:12]
    )
    path = brain.walk_palace("AI Room")
    for step in path:
        print(f"  Room: {step['room']} | Loci: {step['loci']}")

    # 7. Spaced Repetition
    print("\n[7] Spaced Repetition:")
    for label, node in nodes.items():
        brain.schedule_review(node.id)
    # Simulate reviews
    brain.review(nodes["Neural Network"].id, rating=4)
    brain.review(nodes["Backpropagation"].id, rating=3)
    brain.review(nodes["Gradient Descent"].id, rating=5)
    print(f"  Due reviews: {len(brain.learning_module.due_items())}")
    print(f"  Stats: {brain.learning_module.stats()}")

    # 8. Insight Generation
    print("\n[8] Insight Generation:")
    insights = brain.generate_insights(focus_domain="ai")
    for insight in insights:
        print(f"  Insight: {insight.title} (confidence={insight.confidence:.2f})")

    # 9. Cross-domain analogy
    print("\n[9] Cross-Domain Analogy:")
    analogy = CrossDomainAnalogy(brain.knowledge_graph)
    analogies = analogy.find_analogies("ai", "biology", top_k=3)
    for a in analogies:
        print(f"  Analogy: {a['analogy']} (sim={a['similarity']:.2f})")

    # 10. System stats
    print("\n[10] System Stats:")
    stats = brain.stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
