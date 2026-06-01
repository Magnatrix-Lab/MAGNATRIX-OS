"""
lookup_agent_native.py — Semantic Lookup Agent with Knowledge Graph Traversal.

Architectural patterns extracted from matthiasgeihs/smart-lookup and crypto-graph:
- Smart lookup: AI-assisted search over local knowledge and web sources.
- Knowledge graph traversal for relationship discovery between concepts.
- Contextual ranking of results using semantic relevance + graph distance.
- Caching layer with LRU eviction for repeated queries.
- Incremental graph building as new facts are discovered.

Pure Python ≥3.9, stdlib only.
"""
from __future__ import annotations

import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Knowledge Graph
# ---------------------------------------------------------------------------

@dataclass
class KGNode:
    id: str
    label: str
    type: str = "entity"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KGEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0


class NativeKnowledgeGraph:
    """Simple in-memory knowledge graph with BFS traversal."""

    def __init__(self) -> None:
        self.nodes: Dict[str, KGNode] = {}
        self.edges: Dict[str, List[KGEdge]] = {}  # adjacency list

    def add_node(self, node: KGNode) -> None:
        self.nodes[node.id] = node
        if node.id not in self.edges:
            self.edges[node.id] = []

    def add_edge(self, edge: KGEdge) -> None:
        if edge.source not in self.edges:
            self.edges[edge.source] = []
        self.edges[edge.source].append(edge)

    def neighbors(self, node_id: str, relation: Optional[str] = None) -> List[KGNode]:
        """Return neighboring nodes, optionally filtered by relation."""
        results = []
        for e in self.edges.get(node_id, []):
            if relation is None or e.relation == relation:
                n = self.nodes.get(e.target)
                if n:
                    results.append(n)
        return results

    def shortest_path(
        self, start: str, end: str, max_depth: int = 5
    ) -> Optional[List[Tuple[str, str, str]]]:
        """BFS shortest path returning list of (source, relation, target)."""
        visited: Set[str] = {start}
        queue: List[Tuple[str, List[Tuple[str, str, str]]]] = [(start, [])]
        while queue:
            current, path = queue.pop(0)
            if current == end:
                return path
            if len(path) >= max_depth:
                continue
            for e in self.edges.get(current, []):
                if e.target not in visited:
                    visited.add(e.target)
                    queue.append((e.target, path + [(e.source, e.relation, e.target)]))
        return None

    def relatedness(self, a: str, b: str) -> float:
        """Graph distance relatedness (1 / (1 + distance))."""
        path = self.shortest_path(a, b)
        if path is None:
            return 0.0
        return 1.0 / (1.0 + len(path))

    def to_json(self) -> str:
        return json.dumps({
            "nodes": [{"id": n.id, "label": n.label, "type": n.type} for n in self.nodes.values()],
            "edges": [{"s": e.source, "t": e.target, "r": e.relation, "w": e.weight} for edges in self.edges.values() for e in edges],
        })


# ---------------------------------------------------------------------------
# Lookup Engine
# ---------------------------------------------------------------------------

class NativeLookupAgent:
    """
    Smart lookup agent combining keyword search, knowledge graph traversal,
    and LLM-powered summarization.
    """

    def __init__(
        self,
        llm_fn: Optional[Callable[[str], str]] = None,
        web_search_fn: Optional[Callable[[str], List[str]]] = None,
        cache_size: int = 128,
    ) -> None:
        self.llm = llm_fn
        self.web_search = web_search_fn
        self.kg = NativeKnowledgeGraph()
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.cache_size = cache_size
        self._query_stats: Dict[str, int] = {}

    def _get_cache(self, query: str) -> Optional[Dict[str, Any]]:
        if query in self.cache:
            self.cache.move_to_end(query)
            return self.cache[query]
        return None

    def _set_cache(self, query: str, value: Dict[str, Any]) -> None:
        self.cache[query] = value
        self.cache.move_to_end(query)
        if len(self.cache) > self.cache_size:
            self.cache.popitem(last=False)

    def lookup(self, query: str, use_web: bool = False) -> Dict[str, Any]:
        """Perform a smart lookup over the knowledge graph and optional web sources."""
        cached = self._get_cache(query)
        if cached is not None:
            cached["cached"] = True
            return cached

        self._query_stats[query] = self._query_stats.get(query, 0) + 1
        results: Dict[str, Any] = {"query": query, "cached": False, "sources": [], "summary": "", "related": []}

        # 1. Keyword match over nodes
        matched_nodes = [
            n for n in self.kg.nodes.values()
            if query.lower() in n.label.lower() or query.lower() in str(n.metadata).lower()
        ]
        results["sources"].extend([{"type": "kg_node", "id": n.id, "label": n.label} for n in matched_nodes])

        # 2. Graph traversal: find related nodes via 1-hop
        related: List[Dict[str, Any]] = []
        for n in matched_nodes:
            for neighbor in self.kg.neighbors(n.id):
                related.append({"id": neighbor.id, "label": neighbor.label, "via": n.id})
        results["related"] = related

        # 3. Web fallback
        if use_web and self.web_search and not matched_nodes:
            web_results = self.web_search(query)
            results["sources"].extend([{"type": "web", "url": u} for u in web_results])

        # 4. Summarize with LLM if available
        if self.llm:
            context = "\n".join(
                f"- {s['label'] if 'label' in s else s['url']}" for s in results["sources"]
            )
            prompt = f"Query: {query}\nSources:\n{context}\nSummarize the key information in 2-3 sentences."
            results["summary"] = self.llm(prompt)
        else:
            results["summary"] = f"Found {len(results['sources'])} sources and {len(related)} related items."

        self._set_cache(query, results)
        return results

    def add_fact(self, subject: str, relation: str, obj: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a subject-relation-object triple to the knowledge graph."""
        for node_id, label in ((subject, subject), (obj, obj)):
            if node_id not in self.kg.nodes:
                self.kg.add_node(KGNode(id=node_id, label=label, type="entity", metadata=metadata or {}))
        self.kg.add_edge(KGEdge(source=subject, target=obj, relation=relation))
        # Invalidate cache entries that mention these terms
        to_remove = [k for k in self.cache if subject.lower() in k.lower() or obj.lower() in k.lower()]
        for k in to_remove:
            del self.cache[k]

    def find_connection(self, a: str, b: str) -> Optional[Dict[str, Any]]:
        """Find how two concepts are connected in the knowledge graph."""
        path = self.kg.shortest_path(a, b)
        if path is None:
            return None
        return {
            "start": a,
            "end": b,
            "path_length": len(path),
            "steps": [{"from": s, "relation": r, "to": t} for s, r, t in path],
            "relatedness": self.kg.relatedness(a, b),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "nodes": len(self.kg.nodes),
            "edges": sum(len(v) for v in self.kg.edges.values()),
            "cache_size": len(self.cache),
            "query_stats": dict(self._query_stats),
        }


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def test_lookup_agent() -> None:
    agent = NativeLookupAgent()

    # Build a small crypto graph
    agent.add_fact("SHA-256", "uses", "Merkle-Damgard")
    agent.add_fact("BLAKE3", "uses", "Merkle-tree")
    agent.add_fact("Merkle-tree", "faster_than", "Merkle-Damgard")
    agent.add_fact("Ed25519", "based_on", "Curve25519")
    agent.add_fact("Curve25519", "is_a", "Elliptic Curve")
    agent.add_fact("SHA-256", "produces", "256-bit digest")

    # Lookup
    r1 = agent.lookup("SHA-256")
    assert len(r1["sources"]) > 0
    assert not r1["cached"]

    r2 = agent.lookup("SHA-256")
    assert r2["cached"]

    # Connection discovery
    conn = agent.find_connection("SHA-256", "Merkle-Damgard")
    assert conn is not None
    assert conn["path_length"] == 1

    conn2 = agent.find_connection("BLAKE3", "Merkle-Damgard")
    assert conn2 is not None
    assert conn2["path_length"] == 2

    stats = agent.get_stats()
    assert stats["nodes"] == 8
    assert stats["cache_size"] == 1

    print("[test_lookup_agent] PASSED")


if __name__ == "__main__":
    test_lookup_agent()
