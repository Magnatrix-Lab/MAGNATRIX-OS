"""Vector Store — Dense vector database with indexing, search, and CRUD operations.

Modul ini menyediakan:
- VectorIndex untuk HNSW/Flat/IVF indexing
- VectorStore untuk CRUD operations dan search
- VectorFilter untuk metadata filtering
- VectorBatch untuk batch operations
- VectorStoreManager untuk multi-collection management
"""

from __future__ import annotations

import json
import time
import uuid
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class IndexType(Enum):
    FLAT = "flat"
    HNSW = "hnsw"
    IVF = "ivf"


@dataclass
class VectorRecord:
    """Single record in vector store."""
    record_id: str
    vector: List[float]
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class VectorIndex:
    """Indexing structure for fast similarity search."""

    def __init__(self, index_type: IndexType = IndexType.FLAT, dim: int = 384, m: int = 16, ef_construction: int = 200):
        self.index_type = index_type
        self.dim = dim
        self.m = m  # HNSW parameter
        self.ef_construction = ef_construction
        self._records: Dict[str, VectorRecord] = {}
        self._vectors: List[Tuple[str, List[float]]] = []
        self._hnsw_graph: Dict[str, List[str]] = {}  # HNSW layer simulation

    def add(self, record: VectorRecord) -> None:
        self._records[record.record_id] = record
        self._vectors.append((record.record_id, record.vector))
        if self.index_type == IndexType.HNSW:
            self._hnsw_add(record)

    def _hnsw_add(self, record: VectorRecord) -> None:
        # Simulated HNSW: connect to nearest neighbors
        neighbors = self._hnsw_search_neighbors(record.vector, top_k=self.m)
        self._hnsw_graph[record.record_id] = [n[0] for n in neighbors]

    def _hnsw_search_neighbors(self, vector: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        scored = []
        for rid, vec in self._vectors:
            if len(vec) == len(vector):
                dot = sum(x * y for x, y in zip(vec, vector))
                norm_a = math.sqrt(sum(x * x for x in vec)) or 1.0
                norm_b = math.sqrt(sum(x * x for x in vector)) or 1.0
                sim = dot / (norm_a * norm_b)
                scored.append((rid, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search(self, query: List[float], top_k: int = 5, metric: str = "cosine",
               filter_fn: Optional[Callable[[VectorRecord], bool]] = None) -> List[Tuple[str, float]]:
        if metric == "cosine":
            return self._search_cosine(query, top_k, filter_fn)
        elif metric == "euclidean":
            return self._search_euclidean(query, top_k, filter_fn)
        return self._search_cosine(query, top_k, filter_fn)

    def _search_cosine(self, query: List[float], top_k: int, filter_fn: Optional[Callable[[VectorRecord], bool]]) -> List[Tuple[str, float]]:
        scored = []
        for rid, record in self._records.items():
            if filter_fn and not filter_fn(record):
                continue
            vec = record.vector
            if len(vec) != len(query):
                continue
            dot = sum(x * y for x, y in zip(vec, query))
            norm_a = math.sqrt(sum(x * x for x in vec)) or 1.0
            norm_b = math.sqrt(sum(x * x for x in query)) or 1.0
            sim = dot / (norm_a * norm_b)
            scored.append((rid, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _search_euclidean(self, query: List[float], top_k: int, filter_fn: Optional[Callable[[VectorRecord], bool]]) -> List[Tuple[str, float]]:
        scored = []
        for rid, record in self._records.items():
            if filter_fn and not filter_fn(record):
                continue
            vec = record.vector
            if len(vec) != len(query):
                continue
            dist = math.sqrt(sum((x - y) ** 2 for x, y in zip(vec, query)))
            scored.append((rid, dist))
        scored.sort(key=lambda x: x[1])
        return scored[:top_k]

    def delete(self, record_id: str) -> bool:
        if record_id in self._records:
            del self._records[record_id]
            self._vectors = [(rid, v) for rid, v in self._vectors if rid != record_id]
            self._hnsw_graph.pop(record_id, None)
            return True
        return False

    def get(self, record_id: str) -> Optional[VectorRecord]:
        return self._records.get(record_id)

    def count(self) -> int:
        return len(self._records)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "records": len(self._records),
            "index_type": self.index_type.value,
            "dimension": self.dim,
        }


class VectorStore:
    """Vector database with CRUD and search."""

    def __init__(self, store_id: str, name: str, dim: int = 384, index_type: IndexType = IndexType.HNSW):
        self.store_id = store_id
        self.name = name
        self.dim = dim
        self.index = VectorIndex(index_type, dim)
        self._total_adds = 0
        self._total_searches = 0

    def add(self, vector: List[float], text: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
        record = VectorRecord(
            record_id=str(uuid.uuid4())[:12],
            vector=vector[:self.dim],
            text=text,
            metadata=metadata or {},
        )
        self.index.add(record)
        self._total_adds += 1
        return record.record_id

    def add_batch(self, items: List[Tuple[List[float], str, Optional[Dict[str, Any]]]]) -> List[str]:
        return [self.add(v, t, m) for v, t, m in items]

    def search(self, query: List[float], top_k: int = 5, metric: str = "cosine",
               filters: Optional[Dict[str, Any]] = None) -> List[Tuple[str, float, VectorRecord]]:
        filter_fn = None
        if filters:
            filter_fn = lambda r: all(r.metadata.get(k) == v for k, v in filters.items())
        results = self.index.search(query, top_k, metric, filter_fn)
        self._total_searches += 1
        return [(rid, score, self.index.get(rid)) for rid, score in results]

    def delete(self, record_id: str) -> bool:
        return self.index.delete(record_id)

    def get(self, record_id: str) -> Optional[VectorRecord]:
        return self.index.get(record_id)

    def update_metadata(self, record_id: str, metadata: Dict[str, Any]) -> bool:
        record = self.index.get(record_id)
        if record:
            record.metadata.update(metadata)
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "store_id": self.store_id,
            "name": self.name,
            "total_adds": self._total_adds,
            "total_searches": self._total_searches,
            **self.index.get_stats(),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "store_id": self.store_id,
                "name": self.name,
                "stats": self.get_stats(),
                "records": [{"id": r.record_id, "text": r.text[:50], "metadata": r.metadata} for r in self.index._records.values()],
            }, f, indent=2)


class VectorStoreManager:
    """Manage multiple vector collections."""

    def __init__(self):
        self._stores: Dict[str, VectorStore] = {}

    def create(self, name: str, dim: int = 384, index_type: IndexType = IndexType.HNSW) -> VectorStore:
        sid = str(uuid.uuid4())[:12]
        store = VectorStore(sid, name, dim, index_type)
        self._stores[sid] = store
        return store

    def get(self, store_id: str) -> Optional[VectorStore]:
        return self._stores.get(store_id)

    def list_all(self) -> List[VectorStore]:
        return list(self._stores.values())

    def delete_store(self, store_id: str) -> bool:
        return self._stores.pop(store_id, None) is not None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "stores": len(self._stores),
            "total_records": sum(s.index.count() for s in self._stores.values()),
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("VECTOR STORE DEMO")
    print("=" * 70)

    # 1. Create store
    print("\n[1] Create Vector Store")
    manager = VectorStoreManager()
    store = manager.create("knowledge-base", dim=128, index_type=IndexType.HNSW)
    print(f"  Store: {store.store_id}, name={store.name}, dim={store.dim}")

    # 2. Add vectors
    print("\n[2] Add Vectors")
    import random
    random.seed(42)
    for i in range(20):
        vec = [random.uniform(-1, 1) for _ in range(128)]
        store.add(vec, f"Document about topic {i}", {"topic": i % 5, "category": "tech" if i % 2 == 0 else "science"})
    print(f"  Added: {store.index.count()} records")

    # 3. Search
    print("\n[3] Search")
    query = [random.uniform(-1, 1) for _ in range(128)]
    results = store.search(query, top_k=5, metric="cosine")
    print(f"  Query top 5:")
    for rid, score, record in results:
        print(f"    [{score:.4f}] {record.text[:40]}... (topic={record.metadata.get('topic')})")

    # 4. Filtered search
    print("\n[4] Filtered Search")
    filtered = store.search(query, top_k=5, filters={"category": "tech"})
    print(f"  Tech only: {len(filtered)} results")
    for rid, score, record in filtered:
        print(f"    [{score:.4f}] {record.text[:40]}...")

    # 5. Delete
    print("\n[5] Delete")
    to_delete = list(store.index._records.keys())[0]
    store.delete(to_delete)
    print(f"  After delete: {store.index.count()} records")

    # 6. Update metadata
    print("\n[6] Update Metadata")
    rid = list(store.index._records.keys())[0]
    store.update_metadata(rid, {"updated": True, "priority": "high"})
    record = store.get(rid)
    print(f"  Updated metadata: {record.metadata}")

    # 7. Stats
    print(f"\n[7] Store Stats")
    print(f"  {store.get_stats()}")

    # 8. Manager stats
    print(f"\n[8] Manager Stats")
    print(f"  {manager.get_stats()}")

    # 9. Export
    print("\n[9] Export")
    store.export("/tmp/vector_store.json")
    print("  Exported to /tmp/vector_store.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
