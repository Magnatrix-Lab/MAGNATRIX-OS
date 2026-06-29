"""
relationship_inference_native.py
MAGNATRIX-OS — Relationship Inference Engine

Inspired by ai-knowledge-graph: Infer new relationships between entities. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class InferredRelation:
    relation_id: str
    subject: str
    predicate: str
    object: str
    inference_type: str  # transitive, lexical, community, similarity
    confidence: float


class RelationshipInferenceEngine:
    """Infer new relationships between entities in a knowledge graph."""

    def __init__(self, cache_dir: str = "./inferred_relations"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.inferred: List[InferredRelation] = []
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "inferred.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.inferred = [InferredRelation(**r) for r in data]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "inferred.json", "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.inferred], f, indent=2)

    def _find_communities(self, triples: List[Any]) -> Dict[str, List[str]]:
        """Find connected communities of entities."""
        adj = {}
        for t in triples:
            adj.setdefault(t.subject, []).append(t.object)
            adj.setdefault(t.object, []).append(t.subject)
        visited = set()
        communities = {}
        comm_id = 0
        for entity in adj:
            if entity in visited:
                continue
            stack = [entity]
            community = []
            while stack:
                current = stack.pop()
                if current not in visited:
                    visited.add(current)
                    community.append(current)
                    for neighbor in adj.get(current, []):
                        if neighbor not in visited:
                            stack.append(neighbor)
            communities[f"community_{comm_id}"] = community
            comm_id += 1
        return communities

    def infer_transitive(self, triples: List[Any]) -> List[InferredRelation]:
        """Infer transitive relationships: A->B, B->C => A->C."""
        inferred = []
        for t1 in triples:
            for t2 in triples:
                if t1.object == t2.subject and t1.subject != t2.object:
                    inferred.append(InferredRelation(
                        relation_id=f"trans_{t1.triple_id}_{t2.triple_id}",
                        subject=t1.subject, predicate=f"{t1.predicate}_then_{t2.predicate}",
                        object=t2.object, inference_type="transitive", confidence=0.6,
                    ))
        return inferred

    def infer_lexical_similarity(self, entities: List[str], triples: List[Any]) -> List[InferredRelation]:
        """Infer relationships based on lexical similarity."""
        inferred = []
        for i, e1 in enumerate(entities):
            for e2 in entities[i+1:]:
                words1 = set(e1.lower().split())
                words2 = set(e2.lower().split())
                overlap = words1 & words2
                if len(overlap) >= 2 and len(overlap) / max(len(words1), len(words2)) >= 0.5:
                    inferred.append(InferredRelation(
                        relation_id=f"lex_{e1}_{e2}", subject=e1, predicate="related_to",
                        object=e2, inference_type="lexical", confidence=0.5,
                    ))
        return inferred

    def infer_community_bridges(self, triples: List[Any]) -> List[InferredRelation]:
        """Infer bridges between disconnected communities."""
        communities = self._find_communities(triples)
        inferred = []
        community_list = list(communities.values())
        for i in range(len(community_list)):
            for j in range(i + 1, len(community_list)):
                c1 = community_list[i]
                c2 = community_list[j]
                if c1 and c2:
                    inferred.append(InferredRelation(
                        relation_id=f"bridge_{i}_{j}", subject=c1[0], predicate="connected_to",
                        object=c2[0], inference_type="community", confidence=0.4,
                    ))
        return inferred

    def infer_all(self, triples: List[Any]) -> List[InferredRelation]:
        """Run all inference types."""
        entities = list(set(t.subject for t in triples) | set(t.object for t in triples))
        transitive = self.infer_transitive(triples)
        lexical = self.infer_lexical_similarity(entities, triples)
        bridges = self.infer_community_bridges(triples)
        all_inferred = transitive + lexical + bridges
        self.inferred.extend(all_inferred)
        self._save()
        return all_inferred

    def get_stats(self) -> Dict[str, Any]:
        types = {}
        for r in self.inferred:
            types[r.inference_type] = types.get(r.inference_type, 0) + 1
        return {"total_inferred": len(self.inferred), "by_type": types}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["RelationshipInferenceEngine", "InferredRelation"]