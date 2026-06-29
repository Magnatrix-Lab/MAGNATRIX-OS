
"""
memory_retrieval_engine_native.py
MAGNATRIX-OS — Memory Retrieval Engine

Inspired by Synapse memory retrieval:
- Query past states ("what was true on June 20?")
- Temporal queries across the knowledge graph
- Relevance ranking with recency, salience, and connection strength
- Semantic similarity approximation

Pure Python standard library.
"""

import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json


@dataclass
class RetrievalResult:
    memory_id: str
    content: str
    relevance_score: float
    recency_score: float
    salience_score: float
    connection_score: float
    timestamp: str


class MemoryRetrievalEngine:
    """Retrieve memories with multi-factor relevance ranking."""

    def __init__(self, graph=None, hippocampus=None):
        self.graph = graph
        self.hippocampus = hippocampus

    def query_temporal(self, query_time: str, subject: Optional[str] = None) -> List[Dict]:
        """Query what was true at a specific time."""
        if not self.graph:
            return []
        facts = self.graph.what_was_true(query_time)
        if subject:
            facts = [f for f in facts if f.subject == subject or f.object == subject]
        return [{
            "subject": f.subject,
            "predicate": f.predicate,
            "object": f.object,
            "valid_from": f.valid_from,
            "confidence": f.confidence,
        } for f in facts]

    def query_by_entity(self, entity: str, include_neighbors: bool = True) -> List[Dict]:
        """Query all facts and connections about an entity."""
        if not self.graph:
            return []
        results = []
        # Direct facts
        facts = self.graph.get_entity_history(entity)
        for f in facts:
            results.append({
                "type": "fact",
                "subject": f.subject,
                "predicate": f.predicate,
                "object": f.object,
                "valid_from": f.valid_from,
            })
        # Neighbors
        if include_neighbors:
            neighbors = self.graph.get_neighbors(entity)
            for n in neighbors:
                results.append({
                    "type": "connection",
                    "entity": n["entity"],
                    "relation": n["relation"],
                    "weight": n["weight"],
                })
        return results

    def rank_by_relevance(self, query: str, memories: List[Dict],
                          weights: Optional[Dict[str, float]] = None) -> List[RetrievalResult]:
        """Rank memories by relevance to query using keyword matching."""
        w = weights or {"recency": 0.3, "salience": 0.3, "semantic": 0.2, "connection": 0.2}
        query_terms = set(query.lower().split())
        results = []
        now = datetime.now()
        for mem in memories:
            content = mem.get("content", "")
            mem_id = mem.get("memory_id", "")
            # Semantic similarity (keyword overlap)
            content_terms = set(content.lower().split())
            overlap = len(query_terms & content_terms)
            semantic_score = min(1.0, overlap / max(len(query_terms), 1))
            # Recency
            created = mem.get("created_at", now.isoformat())
            age_days = (now - datetime.fromisoformat(created)).total_seconds() / 86400
            recency_score = max(0, 1.0 - (age_days / 30))  # 30-day decay
            # Salience
            salience = mem.get("salience", 0.5)
            # Connection strength (if graph available)
            connection_score = 0.5
            if self.graph and "entities" in mem:
                for entity in mem.get("entities", []):
                    neighbors = self.graph.get_neighbors(entity)
                    if neighbors:
                        connection_score = max(connection_score, min(1.0, len(neighbors) / 5.0))
            # Combined score
            total = (
                w["recency"] * recency_score +
                w["salience"] * salience +
                w["semantic"] * semantic_score +
                w["connection"] * connection_score
            )
            results.append(RetrievalResult(
                memory_id=mem_id,
                content=content[:200],
                relevance_score=total,
                recency_score=recency_score,
                salience_score=salience,
                connection_score=connection_score,
                timestamp=created,
            ))
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results

    def retrieve_for_context(self, query: str, max_items: int = 10) -> List[str]:
        """Retrieve top memories formatted for LLM context."""
        if not self.hippocampus:
            return []
        memories = [asdict(m) for m in self.hippocampus.get_active_memories()]
        ranked = self.rank_by_relevance(query, memories)
        return [f"[{r.relevance_score:.2f}] {r.content}" for r in ranked[:max_items]]

    def query_changes(self, entity: str, time_start: str, time_end: str) -> List[Dict]:
        """Query how an entity changed between two times."""
        if not self.graph:
            return []
        before = self.query_temporal(time_start, entity)
        after = self.query_temporal(time_end, entity)
        # Find differences
        before_state = {f"{f['predicate']}": f['object'] for f in before}
        after_state = {f"{f['predicate']}": f['object'] for f in after}
        changes = []
        for pred in set(before_state.keys()) | set(after_state.keys()):
            old_val = before_state.get(pred, "[none]")
            new_val = after_state.get(pred, "[none]")
            if old_val != new_val:
                changes.append({
                    "predicate": pred,
                    "before": old_val,
                    "after": new_val,
                })
        return changes

    def to_dict(self) -> Dict:
        return {
            "has_graph": self.graph is not None,
            "has_hippocampus": self.hippocampus is not None,
        }


def asdict(obj):
    """Helper to convert dataclass to dict."""
    from dataclasses import asdict as _asdict
    return _asdict(obj)


__all__ = ["MemoryRetrievalEngine", "RetrievalResult"]
