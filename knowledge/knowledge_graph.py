#!/usr/bin/env python3
"""
Knowledge Graph Engine — MAGNATRIX Phase 4-5
Exponential knowledge graph that learns faster than any human institution.
"""

import json
from typing import Dict, List, Set
from datetime import datetime

class KnowledgeGraph:
    """Self-growing knowledge graph with multi-signal linking."""

    def __init__(self):
        self.nodes = {}  # entity → {properties, timestamp}
        self.edges = {}  # (entity_a, entity_b) → {relation, strength}
        self.embeddings = {}  # entity → semantic vector (mock)

    def add_entity(self, entity: str, properties: Dict):
        """Add entity to graph."""
        self.nodes[entity] = {
            "properties": properties,
            "added": datetime.now().isoformat(),
            "connections": 0,
        }

    def link(self, a: str, b: str, relation: str, strength: float = 0.5):
        """Create semantic link between entities."""
        key = tuple(sorted([a, b]))
        self.edges[key] = {"relation": relation, "strength": strength, "timestamp": datetime.now().isoformat()}

        for entity in [a, b]:
            if entity in self.nodes:
                self.nodes[entity]["connections"] += 1

    def query(self, entity: str, depth: int = 2) -> Dict:
        """Query knowledge graph with multi-hop traversal."""
        visited = {entity}
        frontier = {entity}
        result = {"center": entity, "neighbors": [], "hops": []}

        for d in range(depth):
            next_frontier = set()
            hop_results = []

            for current in frontier:
                for (a, b), edge in self.edges.items():
                    if current == a and b not in visited:
                        next_frontier.add(b)
                        visited.add(b)
                        hop_results.append({"from": a, "to": b, "relation": edge["relation"], "strength": edge["strength"]})
                    elif current == b and a not in visited:
                        next_frontier.add(a)
                        visited.add(a)
                        hop_results.append({"from": b, "to": a, "relation": edge["relation"], "strength": edge["strength"]})

            if hop_results:
                result["hops"].append({"depth": d+1, "connections": hop_results})
            frontier = next_frontier

        return result

    def find_similar(self, entity: str, top_k: int = 5) -> List[str]:
        """Find entities with similar connection patterns."""
        # Simplified: return entities with most shared connections
        if entity not in self.nodes:
            return []

        entity_connections = set()
        for (a, b) in self.edges:
            if a == entity:
                entity_connections.add(b)
            elif b == entity:
                entity_connections.add(a)

        scores = {}
        for other in self.nodes:
            if other == entity:
                continue
            other_connections = set()
            for (a, b) in self.edges:
                if a == other:
                    other_connections.add(b)
                elif b == other:
                    other_connections.add(a)

            shared = len(entity_connections & other_connections)
            if shared > 0:
                scores[other] = shared

        return sorted(scores, key=scores.get, reverse=True)[:top_k]

    def auto_expand(self, seed_entity: str):
        """Auto-expand graph from seed entity using web search."""
        # Mock: in production, searches web, extracts entities, links them
        related = [f"{seed_entity}_aspect_{i}" for i in range(1, 4)]
        for r in related:
            self.add_entity(r, {"source": "auto_expand", "parent": seed_entity})
            self.link(seed_entity, r, "has_aspect", 0.7)
        return related

    def save(self):
        with open("knowledge/graph_state.json", "w") as f:
            json.dump({
                "entities": len(self.nodes),
                "links": len(self.edges),
                "nodes": list(self.nodes.keys())[:100],
            }, f, indent=2)

if __name__ == "__main__":
    kg = KnowledgeGraph()
    print("=== Knowledge Graph Engine ===")

    # Build graph
    kg.add_entity("MAGNATRIX", {"type": "system", "domain": "AI"})
    kg.add_entity("trading", {"type": "capability", "domain": "finance"})
    kg.add_entity("security", {"type": "capability", "domain": "defense"})
    kg.add_entity("P2P", {"type": "technology", "domain": "networking"})

    kg.link("MAGNATRIX", "trading", "has_capability", 0.9)
    kg.link("MAGNATRIX", "security", "has_capability", 0.85)
    kg.link("MAGNATRIX", "P2P", "uses_technology", 0.8)
    kg.link("trading", "security", "requires", 0.7)

    # Query
    result = kg.query("MAGNATRIX", depth=2)
    print(f"Entities: {len(kg.nodes)} | Links: {len(kg.edges)}")
    print(f"Query hops: {len(result['hops'])}")

    # Auto-expand
    expanded = kg.auto_expand("MAGNATRIX")
    print(f"Auto-expanded: {expanded}")
    print(f"Total entities: {len(kg.nodes)}")

    kg.save()
