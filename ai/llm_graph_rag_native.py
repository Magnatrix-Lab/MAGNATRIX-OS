#!/usr/bin/env python3
"""
ai/llm_graph_rag_native.py
MAGNATRIX-OS — Graph RAG Engine for the LLM Arena
AMATI pattern: knowledge graph + RAG hybrid for complex relational reasoning

Pure Python, stdlib only. Simulates entity extraction, graph construction,
hybrid retrieval, and multi-hop reasoning.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _token_count(text: str) -> int:
    return len(text) // 4 + 1


# ───────────────────────────────────────────────────────────────
# 1. KNOWLEDGE GRAPH
# ───────────────────────────────────────────────────────────────

@dataclass
class EntityNode:
    entity_id: str
    label: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationEdge:
    source: str
    target: str
    relation_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """Graph with entities and relations for multi-hop reasoning."""

    def __init__(self) -> None:
        self._entities: Dict[str, EntityNode] = {}
        self._edges: List[RelationEdge] = []
        self._adj: Dict[str, List[RelationEdge]] = {}

    def add_entity(self, entity_id: str, label: str, entity_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        self._entities[entity_id] = EntityNode(entity_id, label, entity_type, properties or {})
        self._adj.setdefault(entity_id, [])

    def add_relation(self, source: str, target: str, relation_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        edge = RelationEdge(source, target, relation_type, properties or {})
        self._edges.append(edge)
        self._adj.setdefault(source, []).append(edge)

    def get_entity(self, entity_id: str) -> Optional[EntityNode]:
        return self._entities.get(entity_id)

    def traverse(self, start: str, depth: int = 2) -> List[Tuple[str, str, str]]:
        """Traverse graph from start entity, return (source, relation, target) paths."""
        visited = set()
        results = []
        queue = [(start, 0)]
        while queue:
            current, d = queue.pop(0)
            if d >= depth or current in visited:
                continue
            visited.add(current)
            for edge in self._adj.get(current, []):
                results.append((edge.source, edge.relation_type, edge.target))
                queue.append((edge.target, d + 1))
        return results

    def stats(self) -> Dict[str, Any]:
        return {"entities": len(self._entities), "relations": len(self._edges)}


# ───────────────────────────────────────────────────────────────
# 2. ENTITY EXTRACTOR
# ───────────────────────────────────────────────────────────────

class EntityExtractor:
    """Extract entities and relations from text using regex patterns."""

    ENTITY_PATTERNS = {
        "person": r"[A-Z][a-z]+ [A-Z][a-z]+",
        "company": r"[A-Z][a-z]+ (Corp|Inc|Ltd|LLC|Company)",
        "location": r"[A-Z][a-z]+ (City|Town|Country|State)",
        "product": r"[A-Z][a-z]+ (Pro|Max|Ultra|OS|System)",
        "technology": r"[A-Z][a-z]+ (AI|ML|LLM|API|Framework|Engine)",
    }

    RELATION_PATTERNS = [
        (r"(\w+) works at (\w+)", "works_at"),
        (r"(\w+) founded (\w+)", "founded"),
        (r"(\w+) is located in (\w+)", "located_in"),
        (r"(\w+) uses (\w+)", "uses"),
        (r"(\w+) is a (\w+)", "is_a"),
    ]

    def extract(self, text: str) -> Tuple[List[EntityNode], List[RelationEdge]]:
        entities = []
        entity_ids = {}
        for etype, pattern in self.ENTITY_PATTERNS.items():
            for match in re.finditer(pattern, text):
                label = match.group(0)
                eid = f"{etype}_{label.lower().replace(' ', '_')}"
                if eid not in entity_ids:
                    entity_ids[eid] = EntityNode(eid, label, etype)
                    entities.append(entity_ids[eid])

        relations = []
        for pattern, rel_type in self.RELATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                source_label = match.group(1)
                target_label = match.group(2)
                source_id = f"person_{source_label.lower().replace(' ', '_')}" if source_label[0].isupper() else None
                target_id = f"company_{target_label.lower().replace(' ', '_')}" if target_label[0].isupper() else None
                if source_id and target_id:
                    relations.append(RelationEdge(source_id, target_id, rel_type))
        return entities, relations


# ───────────────────────────────────────────────────────────────
# 3. GRAPH VECTOR HYBRID
# ───────────────────────────────────────────────────────────────

class GraphVectorHybrid:
    """Combine graph traversal with vector similarity retrieval."""

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph
        self._chunks: Dict[str, str] = {}
        self._entity_links: Dict[str, List[str]] = {}  # entity_id -> chunk_ids

    def add_chunk(self, chunk_id: str, text: str, entities: List[str]) -> None:
        self._chunks[chunk_id] = text
        for eid in entities:
            self._entity_links.setdefault(eid, []).append(chunk_id)

    def hybrid_query(self, entity_id: str, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # Graph traversal
        graph_paths = self.graph.traverse(entity_id, depth=2)
        related_entities = set()
        for s, r, t in graph_paths:
            related_entities.add(t)

        # Collect chunks from related entities
        chunk_scores: Dict[str, int] = {}
        for eid in related_entities:
            for cid in self._entity_links.get(eid, []):
                chunk_scores[cid] = chunk_scores.get(cid, 0) + 1

        # Simple keyword matching for query text
        for cid, text in self._chunks.items():
            score = sum(1 for word in query_text.lower().split() if word in text.lower())
            if score > 0:
                chunk_scores[cid] = chunk_scores.get(cid, 0) + score

        ranked = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [{"chunk_id": cid, "text": self._chunks[cid], "score": score} for cid, score in ranked]


# ───────────────────────────────────────────────────────────────
# 4. QUERY PLANNER
# ───────────────────────────────────────────────────────────────

class QueryPlanner:
    """Analyze query to determine if graph or vector search is better."""

    GRAPH_KEYWORDS = ["who", "where", "when", "what", "how", "relationship", "connection", "between", "path"]

    def plan(self, query: str) -> str:
        text = query.lower()
        if any(kw in text for kw in self.GRAPH_KEYWORDS):
            return "graph"
        return "vector"


# ───────────────────────────────────────────────────────────────
# 5. REASONING CHAIN
# ───────────────────────────────────────────────────────────────

class ReasoningChain:
    """Traverse graph to find multi-hop answers."""

    def reason(self, graph: KnowledgeGraph, query: str, start_entity: str) -> Dict[str, Any]:
        paths = graph.traverse(start_entity, depth=3)
        evidence = []
        for s, r, t in paths:
            src = graph.get_entity(s)
            tgt = graph.get_entity(t)
            if src and tgt:
                evidence.append(f"{src.label} {r} {tgt.label}")
        return {
            "query": query,
            "start_entity": start_entity,
            "paths_found": len(paths),
            "evidence": evidence[:10],
            "answer": "; ".join(evidence[:3]) if evidence else "No evidence found.",
        }


# ───────────────────────────────────────────────────────────────
# 6. GRAPH RAG ENGINE
# ───────────────────────────────────────────────────────────────

class GraphRAGEngine:
    """Main orchestrator: extract entities -> build graph -> chunk -> hybrid query -> reason."""

    def __init__(self) -> None:
        self.graph = KnowledgeGraph()
        self.extractor = EntityExtractor()
        self.hybrid = GraphVectorHybrid(self.graph)
        self.planner = QueryPlanner()
        self.reasoner = ReasoningChain()

    def ingest(self, doc_id: str, text: str) -> None:
        entities, relations = self.extractor.extract(text)
        for e in entities:
            self.graph.add_entity(e.entity_id, e.label, e.type, e.properties)
        for r in relations:
            self.graph.add_relation(r.source, r.target, r.relation_type, r.properties)
        self.hybrid.add_chunk(doc_id, text, [e.entity_id for e in entities])

    def query(self, query: str, start_entity: Optional[str] = None) -> Dict[str, Any]:
        strategy = self.planner.plan(query)
        if strategy == "graph" and start_entity:
            reasoning = self.reasoner.reason(self.graph, query, start_entity)
            hybrid_results = self.hybrid.hybrid_query(start_entity, query, top_k=5)
            return {
                "strategy": "graph+vector",
                "query": query,
                "reasoning": reasoning,
                "chunks": hybrid_results,
                "graph_stats": self.graph.stats(),
            }
        else:
            # Vector-only fallback
            all_chunks = []
            for cid, text in self.hybrid._chunks.items():
                score = sum(1 for word in query.lower().split() if word in text.lower())
                if score > 0:
                    all_chunks.append({"chunk_id": cid, "text": text, "score": score})
            all_chunks.sort(key=lambda x: x["score"], reverse=True)
            return {
                "strategy": "vector",
                "query": query,
                "chunks": all_chunks[:5],
                "graph_stats": self.graph.stats(),
            }

    def stats(self) -> Dict[str, Any]:
        return self.graph.stats()


# ───────────────────────────────────────────────────────────────
# 7. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Graph RAG Engine Demo")
    print("=" * 60)

    engine = GraphRAGEngine()

    docs = [
        ("doc_1", "Alice works at TechCorp. TechCorp is located in Boston. Boston is a City."),
        ("doc_2", "Bob founded StartupX. StartupX uses LLM Engine. LLM Engine is an AI Framework."),
        ("doc_3", "Alice uses StartupX products. StartupX is located in Boston."),
    ]

    for doc_id, text in docs:
        engine.ingest(doc_id, text)

    print(f"\n[Graph Stats] {json.dumps(engine.stats(), indent=2)}")

    queries = [
        ("Where does Alice work?", "person_alice"),
        ("What technology does StartupX use?", "company_startupx"),
        ("What is the connection between Alice and Boston?", "person_alice"),
    ]

    for q, entity in queries:
        print(f"\n[QUERY] {q}")
        result = engine.query(q, entity)
        print(f"  Strategy: {result['strategy']}")
        if "reasoning" in result:
            print(f"  Paths: {result['reasoning']['paths_found']}")
            print(f"  Evidence: {result['reasoning']['evidence'][:3]}")
        print(f"  Chunks: {len(result['chunks'])}")
        for c in result['chunks'][:2]:
            print(f"    [{c['chunk_id']}] score={c['score']} | {c['text'][:60]}...")

    print("\n" + "=" * 60)
    print("Demo complete. Graph RAG Engine ready for LLM Arena.")
    print("=" * 60)
