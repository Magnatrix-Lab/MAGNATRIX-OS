"""
knowledge/vector_store_native.py
MAGNATRIX-OS Layer 5 — Vector Database (RAG backbone)
Native pure-Python implementation. Zero external dependencies.
Supports flat (exact) and HNSW (approximate) nearest-neighbor search,
with int8 & binary quantization for memory-constrained environments.
"""
from __future__ import annotations

import json
import math
import os
import pickle
import random
import struct
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Protocol, Tuple, Optional, Callable


# ── Protocols ───────────────────────────────────────────

class IndexBackend(Protocol):
    def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None: ...
    def search(self, query: List[float], k: int = 10, filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None) -> List[Tuple[str, float, Dict[str, Any]]]: ...
    def delete(self, id: str) -> bool: ...
    def count(self) -> int: ...
    def persist(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...


# ── Cosine Similarity Engine ──────────────────────────

class CosineSimilarity:
    """Pure Python cosine similarity with optional SIMD-like unrolling."""

    @staticmethod
    def normalize(v: List[float]) -> List[float]:
        norm = math.sqrt(sum(x * x for x in v))
        if norm == 0.0:
            return v[:]
        return [x / norm for x in v]

    @staticmethod
    def dot(a: List[float], b: List[float]) -> float:
        # Unroll by 4 for cache-friendly micro-optimization
        total = 0.0
        n = len(a)
        i = 0
        while i + 4 <= n:
            total += a[i] * b[i] + a[i + 1] * b[i + 1] + a[i + 2] * b[i + 2] + a[i + 3] * b[i + 3]
            i += 4
        while i < n:
            total += a[i] * b[i]
            i += 1
        return total

    @classmethod
    def score(cls, a: List[float], b: List[float]) -> float:
        return cls.dot(a, b)

    @classmethod
    def batch_score(cls, query: List[float], vectors: List[List[float]]) -> List[float]:
        return [cls.score(query, v) for v in vectors]


# ── Quantizers ────────────────────────────────────────

class Int8Quantizer:
    """Per-vector int8 quantization: min-max scaling to [-128, 127]."""

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def quantize(self, vector: List[float]) -> Tuple[bytes, float, float]:
        min_v = min(vector)
        max_v = max(vector)
        scale = (max_v - min_v) / 255.0 if max_v != min_v else 1.0
        zero = min_v
        packed = bytearray(self.dim)
        for i, val in enumerate(vector):
            packed[i] = max(0, min(255, int((val - zero) / scale)))
        return bytes(packed), scale, zero

    def dequantize(self, packed: bytes, scale: float, zero: float) -> List[float]:
        return [(b * scale) + zero for b in packed]


class BinaryQuantizer:
    """Binary quantization: each dimension becomes 1 bit (sign)."""

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.byte_len = (dim + 7) // 8

    def quantize(self, vector: List[float]) -> bytes:
        packed = bytearray(self.byte_len)
        for i, val in enumerate(vector):
            if val >= 0:
                packed[i // 8] |= 1 << (i % 8)
        return bytes(packed)

    @staticmethod
    def hamming(a: bytes, b: bytes) -> int:
        return sum((x ^ y).bit_count() for x, y in zip(a, b))

    @classmethod
    def similarity(cls, a: bytes, b: bytes) -> float:
        dim = len(a) * 8
        dist = cls.hamming(a, b)
        return 1.0 - (dist / dim)


# ── Flat Index (Exact Search) ─────────────────────────

@dataclass
class FlatIndex:
    """Brute-force exact cosine similarity. Best for <100k vectors."""

    dim: int
    normalize_on_add: bool = True
    _vectors: Dict[str, List[float]] = field(default_factory=dict, repr=False)
    _metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        if len(vector) != self.dim:
            raise ValueError(f"Dimension mismatch: expected {self.dim}, got {len(vector)}")
        v = CosineSimilarity.normalize(vector) if self.normalize_on_add else vector[:]
        self._vectors[id] = v
        self._metadata[id] = metadata or {}

    def search(self, query: List[float], k: int = 10, filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        q = CosineSimilarity.normalize(query)
        scores: List[Tuple[str, float]] = []
        for vid, vec in self._vectors.items():
            meta = self._metadata[vid]
            if filter_fn is not None and not filter_fn(meta):
                continue
            score = CosineSimilarity.dot(q, vec)
            scores.append((vid, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [(vid, sc, self._metadata[vid]) for vid, sc in scores[:k]]

    def delete(self, id: str) -> bool:
        if id in self._vectors:
            del self._vectors[id]
            del self._metadata[id]
            return True
        return False

    def count(self) -> int:
        return len(self._vectors)

    def persist(self, path: str) -> None:
        data = {
            "dim": self.dim,
            "normalize_on_add": self.normalize_on_add,
            "vectors": self._vectors,
            "metadata": self._metadata,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.dim = data["dim"]
        self.normalize_on_add = data["normalize_on_add"]
        self._vectors = data["vectors"]
        self._metadata = data["metadata"]


# ── HNSW Index (Approximate Search) ───────────────────

@dataclass
class HNSWIndex:
    """Hierarchical Navigable Small World — approximate K-NN.
    Pure Python, no C++ extensions. Suitable for 100k-10M vectors.
    """

    dim: int
    m: int = 16               # max neighbors per node
    ef_construction: int = 200
    ef_search: int = 50
    m_L: float = 1.0 / math.log(2.0)  # level multiplier
    normalize_on_add: bool = True

    _nodes: Dict[str, List[float]] = field(default_factory=dict, repr=False)
    _metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _graph: Dict[int, Dict[str, List[str]]] = field(default_factory=dict)  # level -> {id -> [neighbors]}
    _levels: Dict[str, int] = field(default_factory=dict)
    _entry_point: Optional[str] = None
    _rng: random.Random = field(default_factory=lambda: random.Random(42))

    def _random_level(self) -> int:
        # Geometric distribution: P(level) = exp(-level / m_L)
        level = 0
        while self._rng.random() < math.exp(-1.0 / self.m_L):
            level += 1
        return level

    def _search_layer(self, query: List[float], entry: str, ef: int, level: int, filter_fn: Optional[Callable] = None) -> List[Tuple[str, float]]:
        visited = {entry}
        candidates = [(-CosineSimilarity.score(query, self._nodes[entry]), entry)]
        result = [(-candidates[0][0], entry)]

        while candidates:
            curr_neg_dist, curr_id = candidates.pop(0)
            curr_dist = -curr_neg_dist
            worst_in_result = result[-1][0] if len(result) >= ef else float("-inf")
            if curr_dist < worst_in_result:
                break
            for neighbor in self._graph.get(level, {}).get(curr_id, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                if filter_fn is not None and not filter_fn(self._metadata.get(neighbor, {})):
                    continue
                dist = CosineSimilarity.score(query, self._nodes[neighbor])
                worst = result[-1][0] if len(result) >= ef else float("-inf")
                if dist > worst or len(result) < ef:
                    candidates.append((-dist, neighbor))
                    candidates.sort(key=lambda x: x[0])
                    result.append((dist, neighbor))
                    result.sort(key=lambda x: x[0], reverse=True)
                    if len(result) > ef:
                        result = result[:ef]
        return result

    def _select_neighbors(self, candidates: List[Tuple[str, float]], m: int) -> List[str]:
        # Simple heuristic: keep top-m by score
        candidates_sorted = sorted(candidates, key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in candidates_sorted[:m]]

    def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        if len(vector) != self.dim:
            raise ValueError(f"Dimension mismatch: expected {self.dim}, got {len(vector)}")
        v = CosineSimilarity.normalize(vector) if self.normalize_on_add else vector[:]

        self._nodes[id] = v
        self._metadata[id] = metadata or {}
        level = self._random_level()
        self._levels[id] = level

        # Ensure graph levels exist
        for l in range(level + 1):
            if l not in self._graph:
                self._graph[l] = {}
            self._graph[l][id] = []

        if self._entry_point is None:
            self._entry_point = id
            return

        # Find entry point for each level
        curr_ep = self._entry_point
        ep_dist = CosineSimilarity.score(v, self._nodes[curr_ep])
        for l in range(self._levels.get(self._entry_point, 0), level, -1):
            if l in self._graph and curr_ep in self._graph[l]:
                neighbors = self._search_layer(v, curr_ep, 1, l)
                if neighbors:
                    curr_ep = neighbors[0][0]

        # Insert into each level from min(level, entry_level) down to 0
        max_level = max(level, self._levels.get(self._entry_point, 0))
        for l in range(min(level, max_level), -1, -1):
            ef = self.ef_construction if l == level else self.m
            candidates = self._search_layer(v, curr_ep, ef, l)
            neighbors = self._select_neighbors(candidates, self.m)
            self._graph[l][id] = neighbors
            # Bidirectional linking
            for nb in neighbors:
                if nb in self._graph[l]:
                    if id not in self._graph[l][nb]:
                        self._graph[l][nb].append(id)
                    # Prune if exceeds M
                    if len(self._graph[l][nb]) > self.m:
                        # Keep strongest connections
                        nb_scores = [(n, CosineSimilarity.score(self._nodes[nb], self._nodes[n])) for n in self._graph[l][nb]]
                        nb_scores.sort(key=lambda x: x[1], reverse=True)
                        self._graph[l][nb] = [n for n, _ in nb_scores[:self.m]]
            if candidates:
                curr_ep = candidates[0][0]

        if level > self._levels.get(self._entry_point, 0):
            self._entry_point = id

    def search(self, query: List[float], k: int = 10, filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        if not self._nodes:
            return []
        q = CosineSimilarity.normalize(query)
        ep = self._entry_point
        if ep is None:
            return []

        # Descend to level 0
        ep_level = self._levels.get(ep, 0)
        for l in range(ep_level, 0, -1):
            if l in self._graph and ep in self._graph[l]:
                neighbors = self._search_layer(q, ep, 1, l)
                if neighbors:
                    ep = neighbors[0][0]

        # Search level 0 with ef_search
        results = self._search_layer(q, ep, self.ef_search, 0, filter_fn=filter_fn)
        top = results[:k]
        return [(vid, sc, self._metadata[vid]) for vid, sc in top]

    def delete(self, id: str) -> bool:
        if id not in self._nodes:
            return False
        del self._nodes[id]
        del self._metadata[id]
        for level in self._graph.values():
            if id in level:
                del level[id]
            for neighbors in level.values():
                if id in neighbors:
                    neighbors.remove(id)
        if self._entry_point == id:
            self._entry_point = next(iter(self._nodes)) if self._nodes else None
        return True

    def count(self) -> int:
        return len(self._nodes)

    def persist(self, path: str) -> None:
        data = {
            "dim": self.dim,
            "m": self.m,
            "ef_construction": self.ef_construction,
            "ef_search": self.ef_search,
            "nodes": self._nodes,
            "metadata": self._metadata,
            "graph": self._graph,
            "levels": self._levels,
            "entry_point": self._entry_point,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.dim = data["dim"]
        self.m = data["m"]
        self.ef_construction = data["ef_construction"]
        self.ef_search = data["ef_search"]
        self._nodes = data["nodes"]
        self._metadata = data["metadata"]
        self._graph = data["graph"]
        self._levels = data["levels"]
        self._entry_point = data["entry_point"]


# ── Vector Store (Unified API) ──────────────────────────

@dataclass
class VectorStore:
    """Unified vector database with pluggable backends."""

    dim: int
    backend: str = "hnsw"          # "flat" or "hnsw"
    use_int8: bool = False
    use_binary: bool = False
    persist_dir: Optional[str] = None

    _index: Any = field(default=None, repr=False)
    _int8: Optional[Int8Quantizer] = field(default=None, repr=False)
    _binary: Optional[BinaryQuantizer] = field(default=None, repr=False)
    _int8_cache: Dict[str, Tuple[bytes, float, float]] = field(default_factory=dict, repr=False)
    _binary_cache: Dict[str, bytes] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.backend == "flat":
            self._index = FlatIndex(dim=self.dim)
        elif self.backend == "hnsw":
            self._index = HNSWIndex(dim=self.dim)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
        if self.use_int8:
            self._int8 = Int8Quantizer(self.dim)
        if self.use_binary:
            self._binary = BinaryQuantizer(self.dim)

    def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        self._index.add(id, vector, metadata)
        if self._int8 is not None:
            self._int8_cache[id] = self._int8.quantize(vector)
        if self._binary is not None:
            self._binary_cache[id] = self._binary.quantize(vector)

    def search(self, query: List[float], k: int = 10, filter_fn: Optional[Callable] = None, exact: bool = False) -> List[Tuple[str, float, Dict[str, Any]]]:
        if exact or self.backend == "flat":
            return self._index.search(query, k, filter_fn)
        return self._index.search(query, k, filter_fn)

    def binary_search(self, query: List[float], k: int = 10) -> List[Tuple[str, float]]:
        if self._binary is None:
            raise RuntimeError("Binary quantizer not enabled")
        q_bin = self._binary.quantize(query)
        scored = []
        for vid, b_vec in self._binary_cache.items():
            sim = BinaryQuantizer.similarity(q_bin, b_vec)
            scored.append((vid, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def delete(self, id: str) -> bool:
        ok = self._index.delete(id)
        if ok:
            self._int8_cache.pop(id, None)
            self._binary_cache.pop(id, None)
        return ok

    def count(self) -> int:
        return self._index.count()

    def persist(self, name: str = "vector_store") -> None:
        if self.persist_dir is None:
            raise RuntimeError("persist_dir not set")
        base = Path(self.persist_dir)
        base.mkdir(parents=True, exist_ok=True)
        self._index.persist(str(base / f"{name}_index.pkl"))
        meta = {
            "dim": self.dim,
            "backend": self.backend,
            "use_int8": self.use_int8,
            "use_binary": self.use_binary,
            "count": self.count(),
            "timestamp": time.time(),
        }
        with open(base / f"{name}_meta.json", "w") as f:
            json.dump(meta, f, indent=2)
        if self._int8_cache:
            with open(base / f"{name}_int8.pkl", "wb") as f:
                pickle.dump(self._int8_cache, f)
        if self._binary_cache:
            with open(base / f"{name}_binary.pkl", "wb") as f:
                pickle.dump(self._binary_cache, f)

    def load(self, name: str = "vector_store") -> None:
        if self.persist_dir is None:
            raise RuntimeError("persist_dir not set")
        base = Path(self.persist_dir)
        self._index.load(str(base / f"{name}_index.pkl"))
        if (base / f"{name}_int8.pkl").exists() and self._int8 is not None:
            with open(base / f"{name}_int8.pkl", "rb") as f:
                self._int8_cache = pickle.load(f)
        if (base / f"{name}_binary.pkl").exists() and self._binary is not None:
            with open(base / f"{name}_binary.pkl", "rb") as f:
                self._binary_cache = pickle.load(f)

    def stats(self) -> Dict[str, Any]:
        return {
            "dim": self.dim,
            "backend": self.backend,
            "count": self.count(),
            "use_int8": self.use_int8,
            "use_binary": self.use_binary,
            "int8_cache_size": len(self._int8_cache),
            "binary_cache_size": len(self._binary_cache),
        }

    def similarity_between(self, id_a: str, id_b: str) -> float:
        if id_a not in self._index._vectors and id_a not in self._index._nodes:
            raise KeyError(id_a)
        vec_a = self._index._vectors.get(id_a) or self._index._nodes.get(id_a)
        vec_b = self._index._vectors.get(id_b) or self._index._nodes.get(id_b)
        if vec_b is None:
            raise KeyError(id_b)
        return CosineSimilarity.score(vec_a, vec_b)


# ── Collection Manager ────────────────────────────────

class CollectionManager:
    """Manages multiple named VectorStore collections."""

    def __init__(self, base_dir: str = "./vector_db") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._collections: Dict[str, VectorStore] = {}

    def create(self, name: str, dim: int, backend: str = "hnsw", use_int8: bool = False) -> VectorStore:
        vs = VectorStore(dim=dim, backend=backend, use_int8=use_int8, persist_dir=str(self.base_dir / name))
        self._collections[name] = vs
        return vs

    def get(self, name: str) -> Optional[VectorStore]:
        if name in self._collections:
            return self._collections[name]
        # Try loading from disk
        meta_path = self.base_dir / name / f"{name}_meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            vs = VectorStore(
                dim=meta["dim"],
                backend=meta["backend"],
                use_int8=meta.get("use_int8", False),
                persist_dir=str(self.base_dir / name),
            )
            vs.load(name)
            self._collections[name] = vs
            return vs
        return None

    def delete_collection(self, name: str) -> bool:
        import shutil
        path = self.base_dir / name
        if path.exists():
            shutil.rmtree(path)
            self._collections.pop(name, None)
            return True
        return False

    def list_collections(self) -> List[str]:
        return [p.name for p in self.base_dir.iterdir() if p.is_dir()]


# ── Embeddings Stub (for text->vector) ─────────────────

class TextEmbedderStub:
    """Placeholder for text embedding model.
    In production, swap with sentence-transformers or openai embedding API.
    """

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self._cache: Dict[str, List[float]] = {}

    def embed(self, text: str) -> List[float]:
        if text in self._cache:
            return self._cache[text]
        # Deterministic hash-based pseudo-embedding for testing
        h = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(self.dim):
            val = ((h[i % 32] + i * 7) % 255) / 127.5 - 1.0
            vec.append(val)
        vec = CosineSimilarity.normalize(vec)
        self._cache[text] = vec
        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


# ── RAG Pipeline Stub ─────────────────────────────────

class RAGPipelineStub:
    """End-to-end RAG: text -> embedding -> retrieve -> context assembly."""

    def __init__(self, store: VectorStore, embedder: TextEmbedderStub, top_k: int = 5) -> None:
        self.store = store
        self.embedder = embedder
        self.top_k = top_k

    def ingest(self, documents: List[Dict[str, Any]]) -> None:
        for doc in documents:
            doc_id = doc.get("id", hashlib.sha256(doc.get("text", "").encode()).hexdigest()[:16])
            vec = self.embedder.embed(doc.get("text", ""))
            self.store.add(doc_id, vec, metadata=doc)

    def query(self, question: str, k: Optional[int] = None) -> List[Dict[str, Any]]:
        q_vec = self.embedder.embed(question)
        results = self.store.search(q_vec, k or self.top_k)
        return [
            {
                "id": vid,
                "score": score,
                "metadata": meta,
            }
            for vid, score, meta in results
        ]

    def ask(self, question: str, llm_fn: Optional[Callable[[str], str]] = None) -> str:
        ctx = self.query(question)
        context_text = "\n".join(f"- {r['metadata'].get('text', '')}" for r in ctx)
        prompt = f"Context:\n{context_text}\n\nQuestion: {question}\nAnswer:"
        if llm_fn:
            return llm_fn(prompt)
        return f"[RAG_STUB] Would query LLM with prompt length {len(prompt)}"


# ── Vector Kernel Bridge ──────────────────────────────

class VectorKernelBridge:
    """Bridge to kernel event_bus for layer-5 vector operations."""

    def __init__(self, store: VectorStore, event_bus: Any = None) -> None:
        self.store = store
        self.event_bus = event_bus

    def on_vector_search(self, query_vec: List[float], k: int) -> List[Tuple[str, float, Dict[str, Any]]]:
        return self.store.search(query_vec, k)

    def on_vector_add(self, id: str, vec: List[float], meta: Optional[Dict[str, Any]] = None) -> None:
        self.store.add(id, vec, meta)
        if self.event_bus:
            self.event_bus.emit("vector.added", {"id": id, "dim": len(vec)})

    def stats(self) -> Dict[str, Any]:
        return self.store.stats()


# ── Health Check ────────────────────────────────────────

class VectorHealthCheck:
    """Self-test suite for vector store integrity."""

    @classmethod
    def run(cls, dim: int = 128, n: int = 100) -> Dict[str, Any]:
        store = VectorStore(dim=dim, backend="flat")
        t0 = time.perf_counter()
        for i in range(n):
            vec = [random.random() for _ in range(dim)]
            store.add(f"vec_{i}", vec, {"idx": i})
        add_time = time.perf_counter() - t0

        query = [random.random() for _ in range(dim)]
        t0 = time.perf_counter()
        results = store.search(query, k=10)
        search_time = time.perf_counter() - t0

        return {
            "dim": dim,
            "vectors_added": n,
            "add_time_sec": round(add_time, 4),
            "search_time_sec": round(search_time, 6),
            "results_found": len(results),
            "top_score": round(results[0][1], 4) if results else None,
            "status": "PASS" if len(results) == 10 else "FAIL",
        }


# ── Demo ────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== MAGNATRIX Vector Store Self-Test ===")
    hc = VectorHealthCheck.run(dim=64, n=500)
    for k, v in hc.items():
        print(f"  {k}: {v}")
    print("=========================================")
