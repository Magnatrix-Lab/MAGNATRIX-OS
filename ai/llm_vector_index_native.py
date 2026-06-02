"""Vector Index — HNSW-style approximate nearest neighbor search using pure Python.

Modul ini menyediakan:
- VectorStore untuk penyimpanan vector dengan metadata
- HNSWIndex untuk Hierarchical Navigable Small World index
- SimilarityEngine untuk cosine/dot/euclidean similarity
- VectorSearcher untuk ANN search
- VectorIndexManager untuk end-to-end vector management
"""

from __future__ import annotations

import json
import time
import uuid
import heapq
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class DistanceMetric(Enum):
    COSINE = auto()
    EUCLIDEAN = auto()
    DOT = auto()
    MANHATTAN = auto()


@dataclass
class VectorRecord:
    """Single vector record with metadata."""
    record_id: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SearchResult:
    """Result of a vector search."""
    record_id: str
    score: float
    vector: List[float]
    metadata: Dict[str, Any]


class SimilarityEngine:
    """Compute vector similarities."""

    @staticmethod
    def cosine(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def euclidean(a: List[float], b: List[float]) -> float:
        return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

    @staticmethod
    def dot(a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def manhattan(a: List[float], b: List[float]) -> float:
        return sum(abs(x - y) for x, y in zip(a, b))

    @staticmethod
    def compute(a: List[float], b: List[float], metric: DistanceMetric) -> float:
        if metric == DistanceMetric.COSINE:
            return SimilarityEngine.cosine(a, b)
        elif metric == DistanceMetric.EUCLIDEAN:
            return -SimilarityEngine.euclidean(a, b)  # Negative for max-heap
        elif metric == DistanceMetric.DOT:
            return SimilarityEngine.dot(a, b)
        elif metric == DistanceMetric.MANHATTAN:
            return -SimilarityEngine.manhattan(a, b)
        return 0.0


class VectorStore:
    """Store vectors with metadata."""

    def __init__(self):
        self._records: Dict[str, VectorRecord] = {}

    def add(self, record: VectorRecord) -> None:
        self._records[record.record_id] = record

    def get(self, record_id: str) -> Optional[VectorRecord]:
        return self._records.get(record_id)

    def remove(self, record_id: str) -> bool:
        return self._records.pop(record_id, None) is not None

    def list_all(self) -> List[VectorRecord]:
        return list(self._records.values())

    def count(self) -> int:
        return len(self._records)

    def get_stats(self) -> Dict[str, Any]:
        if not self._records:
            return {"count": 0}
        dims = [len(r.vector) for r in self._records.values()]
        return {
            "count": len(self._records),
            "avg_dim": sum(dims) / len(dims),
            "min_dim": min(dims),
            "max_dim": max(dims),
        }


class HNSWIndex:
    """HNSW-style approximate nearest neighbor index."""

    def __init__(self, M: int = 16, ef_construction: int = 200, ef_search: int = 50,
                 metric: DistanceMetric = DistanceMetric.COSINE):
        self.M = M
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.metric = metric
        self._level_multiplier = 1 / math.log(M) if M > 1 else 1.0
        self._nodes: Dict[str, Dict[str, Any]] = {}  # id -> {vector, level, neighbors}
        self._entry_point: Optional[str] = None
        self._max_level = 0
        self._similarity = SimilarityEngine()

    def _random_level(self) -> int:
        level = 0
        while random.random() < self._level_multiplier and level < 16:
            level += 1
        return level

    def _search_layer(self, query: List[float], entry_point: str, level: int, ef: int) -> List[Tuple[float, str]]:
        visited = {entry_point}
        candidates = [(-self._similarity.compute(query, self._nodes[entry_point]["vector"], self.metric), entry_point)]
        results = [(-candidates[0][0], entry_point)]

        while candidates:
            _, curr = heapq.heappop(candidates)
            curr_dist = -self._similarity.compute(query, self._nodes[curr]["vector"], self.metric)
            worst = results[0][0] if results else float('inf')
            if curr_dist > worst and len(results) >= ef:
                continue

            for neighbor in self._nodes[curr]["neighbors"].get(level, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    dist = self._similarity.compute(query, self._nodes[neighbor]["vector"], self.metric)
                    heapq.heappush(candidates, (-dist, neighbor))
                    if len(results) < ef:
                        heapq.heappush(results, (dist, neighbor))
                    elif dist > results[0][0]:
                        heapq.heapreplace(results, (dist, neighbor))

        return results

    def add(self, record_id: str, vector: List[float]) -> None:
        level = self._random_level()
        node = {
            "vector": vector,
            "level": level,
            "neighbors": {l: [] for l in range(level + 1)},
        }
        self._nodes[record_id] = node

        if self._entry_point is None:
            self._entry_point = record_id
            self._max_level = level
            return

        # Search from top level to insertion level
        curr_ep = self._entry_point
        for l in range(self._max_level, level, -1):
            neighbors = self._search_layer(vector, curr_ep, l, 1)
            if neighbors:
                curr_ep = neighbors[0][1]

        # Add from level down to 0
        for l in range(min(level, self._max_level), -1, -1):
            neighbors = self._search_layer(vector, curr_ep, l, self.ef_construction)
            # Connect to nearest M neighbors
            selected = heapq.nlargest(self.M, neighbors)
            for _, nid in selected:
                node["neighbors"][l].append(nid)
                if l in self._nodes[nid]["neighbors"]:
                    self._nodes[nid]["neighbors"][l].append(record_id)

        if level > self._max_level:
            self._max_level = level
            self._entry_point = record_id

    def search(self, query: List[float], k: int = 5) -> List[Tuple[float, str]]:
        if not self._entry_point or not self._nodes:
            return []
        curr_ep = self._entry_point
        for l in range(self._max_level, 0, -1):
            neighbors = self._search_layer(query, curr_ep, l, 1)
            if neighbors:
                curr_ep = neighbors[0][1]
        results = self._search_layer(query, curr_ep, 0, max(k, self.ef_search))
        return heapq.nlargest(k, results)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "nodes": len(self._nodes),
            "max_level": self._max_level,
            "entry_point": self._entry_point,
        }


class VectorSearcher:
    """Search vectors using brute force or HNSW."""

    def __init__(self, store: VectorStore, index: Optional[HNSWIndex] = None):
        self.store = store
        self.index = index
        self._similarity = SimilarityEngine()

    def brute_force_search(self, query: List[float], k: int = 5, metric: DistanceMetric = DistanceMetric.COSINE) -> List[SearchResult]:
        scores = []
        for record in self.store.list_all():
            score = self._similarity.compute(query, record.vector, metric)
            scores.append((score, record))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [
            SearchResult(r.record_id, s, r.vector, r.metadata)
            for s, r in scores[:k]
        ]

    def ann_search(self, query: List[float], k: int = 5) -> List[SearchResult]:
        if not self.index:
            return self.brute_force_search(query, k)
        results = self.index.search(query, k)
        return [
            SearchResult(
                rid,
                score,
                self.index._nodes[rid]["vector"],
                self.store.get(rid).metadata if self.store.get(rid) else {}
            )
            for score, rid in results
        ]

    def search_by_metadata(self, filters: Dict[str, Any]) -> List[VectorRecord]:
        results = []
        for record in self.store.list_all():
            match = all(record.metadata.get(k) == v for k, v in filters.items())
            if match:
                results.append(record)
        return results


class VectorIndexManager:
    """End-to-end vector index management."""

    def __init__(self, dim: int = 128, metric: DistanceMetric = DistanceMetric.COSINE):
        self.dim = dim
        self.metric = metric
        self.store = VectorStore()
        self.index = HNSWIndex(metric=metric)
        self.searcher = VectorSearcher(self.store, self.index)

    def add(self, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> str:
        record_id = str(uuid.uuid4())[:12]
        record = VectorRecord(record_id, vector, metadata or {})
        self.store.add(record)
        self.index.add(record_id, vector)
        return record_id

    def search(self, query: List[float], k: int = 5, use_ann: bool = True) -> List[SearchResult]:
        if use_ann:
            return self.searcher.ann_search(query, k)
        return self.searcher.brute_force_search(query, k, self.metric)

    def remove(self, record_id: str) -> bool:
        self.store.remove(record_id)
        return self.index._nodes.pop(record_id, None) is not None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "store": self.store.get_stats(),
            "index": self.index.get_stats(),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "records": [
                    {"id": r.record_id, "vector_dim": len(r.vector), "metadata": r.metadata}
                    for r in self.store.list_all()
                ],
            }, f, indent=2)


import math

# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("VECTOR INDEX DEMO")
    print("=" * 70)

    # 1. Similarity
    print("\n[1] Similarity Metrics")
    a = [1.0, 0.0, 0.0]
    b = [0.9, 0.1, 0.0]
    c = [0.0, 1.0, 0.0]
    print(f"  Cosine(a,b): {SimilarityEngine.cosine(a, b):.4f}")
    print(f"  Cosine(a,c): {SimilarityEngine.cosine(a, c):.4f}")
    print(f"  Euclidean(a,b): {SimilarityEngine.euclidean(a, b):.4f}")
    print(f"  Dot(a,b): {SimilarityEngine.dot(a, b):.4f}")

    # 2. Vector store
    print("\n[2] Vector Store")
    store = VectorStore()
    for i in range(10):
        vec = [1.0 if j == i % 3 else 0.1 for j in range(5)]
        store.add(VectorRecord(f"doc-{i}", vec, {"topic": ["tech", "health", "finance"][i % 3]}))
    print(f"  Store stats: {store.get_stats()}")

    # 3. Brute force search
    print("\n[3] Brute Force Search")
    searcher = VectorSearcher(store)
    query = [1.0, 0.0, 0.0, 0.0, 0.0]
    results = searcher.brute_force_search(query, k=3, metric=DistanceMetric.COSINE)
    print(f"  Query: {query}")
    for r in results:
        print(f"    {r.record_id}: score={r.score:.4f}, topic={r.metadata.get('topic')}")

    # 4. HNSW Index
    print("\n[4] HNSW Index")
    manager = VectorIndexManager(dim=5, metric=DistanceMetric.COSINE)
    for i in range(100):
        vec = [random.random() for _ in range(5)]
        manager.add(vec, {"id": i, "category": ["A", "B", "C"][i % 3]})
    print(f"  Stats: {manager.get_stats()}")

    # 5. ANN search
    print("\n[5] ANN Search")
    query = [0.9, 0.1, 0.1, 0.1, 0.1]
    ann_results = manager.search(query, k=5, use_ann=True)
    print(f"  ANN results: {len(ann_results)}")
    for r in ann_results:
        print(f"    {r.record_id}: score={r.score:.4f}, meta={r.metadata}")

    # Compare with brute force
    bf_results = manager.search(query, k=5, use_ann=False)
    print(f"\n  Brute force results: {len(bf_results)}")
    for r in bf_results:
        print(f"    {r.record_id}: score={r.score:.4f}")

    # 6. Metadata search
    print("\n[6] Metadata Search")
    meta_results = manager.searcher.search_by_metadata({"category": "A"})
    print(f"  Category A records: {len(meta_results)}")

    # 7. Export
    print("\n[7] Export")
    manager.export("/tmp/vector_index.json")
    print("  Exported to /tmp/vector_index.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    random.seed(42)
    _demo()
