"""
knowledge/turbovec_native.py
===========================
MAGNATRIX Native TurboQuant Vector Index
Layer 5: Knowledge (extends knowledge/native_engines.py)

Pola AMATI-PELAJARI-TIRU dari RyanCodrai/turbovec:
- Amati:  TurboQuant vector index in Rust, data-oblivious quantization,
          2-4 bits per dimension, 16x compression, zero training,
          SIMD kernels (NEON/AVX-512), IdMapIndex dengan O(1) delete,
          filtered search dengan allowlist
- Pelajari: Core algorithm: (1) Normalize -> strip length, (2) Random rotation
            dengan orthogonal matrix, (3) Lloyd-Max scalar quantization
            (precomputed dari Beta distribution), (4) Bit-pack coordinates,
            (5) Length-renormalized scoring untuk unbiased inner products
- Tiru:   Native Python dengan numpy (bukan Rust wrapper), reimplementasi
            algoritma TurboQuant untuk MAGNATRIX knowledge layer.
            Integration dengan: RAG pipeline, memory store, document indexing,
            agent episodic memory, knowledge graph embeddings

Key classes:
- TurboQuantIndex: compressed vector search dengan add/search/persist
- IdMapIndex: stable uint64 IDs, O(1) remove, filtered search
- MAGNATRIXVectorStore: integration wrapper untuk knowledge layer
"""

import asyncio
import json
import time
import uuid
import hashlib
import math
import struct
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Callable, Any, Set
from enum import Enum
from collections import defaultdict
import random

# Try numpy, fallback to pure Python
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@dataclass
class QuantizedVector:
    """Single quantized vector storage"""
    slot_id: int = 0
    norm: float = 0.0
    quantized: bytes = b""  # Bit-packed quantized coordinates
    renormalize_factor: float = 1.0  # ||v|| / <u, x_hat>
    original_dim: int = 0
    bit_width: int = 4


@dataclass
class SearchResult:
    """Search result item"""
    slot_id: int = 0
    score: float = 0.0
    external_id: Optional[int] = None  # For IdMapIndex


class LloydMaxQuantizer:
    """
    Lloyd-Max scalar quantizer for known distribution.
    Tiru turbovec: precompute boundaries & centroids dari Beta distribution.
    """

    def __init__(self, bit_width: int = 4):
        self.bit_width = bit_width
        self.num_levels = 2 ** bit_width  # 4 for 2-bit, 16 for 4-bit
        self.boundaries: List[float] = []
        self.centroids: List[float] = []
        self._precompute()

    def _precompute(self):
        """Precompute Lloyd-Max boundaries & centroids"""
        # For Gaussian N(0, 1/d) in high dimensions after random rotation
        # Simplified: uniform partitioning (true Lloyd-Max requires iterative optimization)
        # In production: compute from Beta distribution convergence
        sigma = 1.0  # Normalized post-rotation
        range_limit = 3.0 * sigma
        step = 2 * range_limit / self.num_levels
        self.boundaries = [-range_limit + i * step for i in range(self.num_levels + 1)]
        self.centroids = [(self.boundaries[i] + self.boundaries[i + 1]) / 2
                          for i in range(self.num_levels)]

    def quantize(self, value: float) -> int:
        """Quantize single coordinate"""
        for i in range(self.num_levels):
            if value < self.boundaries[i + 1]:
                return i
        return self.num_levels - 1

    def dequantize(self, level: int) -> float:
        """Dequantize to centroid"""
        return self.centroids[min(level, self.num_levels - 1)]


class TurboQuantIndex:
    """
    Native Python TurboQuant vector index.
    Tiru turbovec core: compress vectors to 2-4 bits, zero training.
    """

    def __init__(self, dim: int = 1536, bit_width: int = 4):
        self.dim = dim
        self.bit_width = bit_width
        self.num_levels = 2 ** bit_width
        self.quantizer = LloydMaxQuantizer(bit_width)
        # Random orthogonal rotation matrix (simplified: random projection)
        self.rotation = self._generate_rotation_matrix(dim)
        # Storage
        self.vectors: Dict[int, QuantizedVector] = {}
        self.next_slot: int = 0
        self.total_added: int = 0

    def _generate_rotation_matrix(self, dim: int) -> Any:
        """Generate random orthogonal matrix for rotation"""
        if HAS_NUMPY:
            # Use QR decomposition for proper orthogonal matrix
            A = np.random.randn(dim, dim)
            Q, _ = np.linalg.qr(A)
            return Q.astype(np.float32)
        else:
            # Fallback: identity with small random perturbation
            return [[1.0 if i == j else random.gauss(0, 0.01)
                     for j in range(dim)] for i in range(dim)]

    def _rotate(self, vector: List[float]) -> List[float]:
        """Apply random rotation to vector"""
        if HAS_NUMPY:
            v = np.array(vector, dtype=np.float32)
            return (v @ self.rotation).tolist()
        else:
            # Pure Python matrix multiplication
            result = []
            for row in self.rotation:
                s = sum(row[i] * vector[i] for i in range(self.dim))
                result.append(s)
            return result

    def _compute_norm(self, vector: List[float]) -> float:
        """Compute L2 norm"""
        if HAS_NUMPY:
            return float(np.linalg.norm(np.array(vector, dtype=np.float32)))
        return math.sqrt(sum(x * x for x in vector))

    def _normalize(self, vector: List[float], norm: float) -> List[float]:
        """Normalize to unit sphere"""
        if norm == 0:
            return [0.0] * len(vector)
        return [x / norm for x in vector]

    def _quantize_vector(self, vector: List[float]) -> Tuple[bytes, float]:
        """Quantize normalized rotated vector"""
        rotated = self._rotate(vector)
        # Quantize each coordinate
        levels = [self.quantizer.quantize(x) for x in rotated]
        # Bit-pack
        packed = self._bit_pack(levels, self.bit_width)
        # Compute renormalize factor: <u, x_hat> (dot product with centroid reconstruction)
        reconstructed = [self.quantizer.dequantize(l) for l in levels]
        dot_product = sum(rotated[i] * reconstructed[i] for i in range(self.dim))
        renormalize = 1.0 / max(dot_product, 1e-10)
        return packed, renormalize

    def _bit_pack(self, levels: List[int], bit_width: int) -> bytes:
        """Pack quantized levels into bytes"""
        if bit_width == 2:
            # 4 values per byte
            packed = bytearray()
            for i in range(0, len(levels), 4):
                byte = 0
                for j in range(4):
                    if i + j < len(levels):
                        byte |= (levels[i + j] & 0x03) << (j * 2)
                packed.append(byte)
            return bytes(packed)
        elif bit_width == 4:
            # 2 values per byte
            packed = bytearray()
            for i in range(0, len(levels), 2):
                byte = (levels[i] & 0x0F)
                if i + 1 < len(levels):
                    byte |= (levels[i + 1] & 0x0F) << 4
                packed.append(byte)
            return bytes(packed)
        else:
            # Full byte per value
            return bytes(levels)

    def _bit_unpack(self, data: bytes, bit_width: int, count: int) -> List[int]:
        """Unpack quantized levels from bytes"""
        if bit_width == 2:
            levels = []
            for byte in data:
                for j in range(4):
                    levels.append((byte >> (j * 2)) & 0x03)
            return levels[:count]
        elif bit_width == 4:
            levels = []
            for byte in data:
                levels.append(byte & 0x0F)
                levels.append((byte >> 4) & 0x0F)
            return levels[:count]
        else:
            return list(data)[:count]

    def add(self, vectors: List[List[float]]) -> List[int]:
        """Add vectors to index - returns slot IDs"""
        slot_ids = []
        for vector in vectors:
            if len(vector) != self.dim:
                raise ValueError(f"Expected dim {self.dim}, got {len(vector)}")
            norm = self._compute_norm(vector)
            normalized = self._normalize(vector, norm)
            packed, renormalize = self._quantize_vector(normalized)
            qv = QuantizedVector(
                slot_id=self.next_slot,
                norm=norm,
                quantized=packed,
                renormalize_factor=renormalize,
                original_dim=self.dim,
                bit_width=self.bit_width
            )
            self.vectors[self.next_slot] = qv
            slot_ids.append(self.next_slot)
            self.next_slot += 1
            self.total_added += 1
        return slot_ids

    def _score_query(self, query_rotated: List[float], qv: QuantizedVector) -> float:
        """Compute inner product score antara query dan quantized vector"""
        levels = self._bit_unpack(qv.quantized, self.bit_width, self.dim)
        # Score = sum(query_rotated[i] * centroid[level[i]])
        score = 0.0
        for i in range(self.dim):
            centroid = self.quantizer.dequantize(levels[i])
            score += query_rotated[i] * centroid
        # Length renormalization untuk unbiased estimate
        score *= qv.renormalize_factor
        # Scale by original norm untuk proper inner product
        score *= qv.norm
        return score

    def search(self, query: List[float], k: int = 10,
               allowlist: Optional[Set[int]] = None) -> Tuple[List[float], List[int]]:
        """
        Search top-k vectors.
        Tiru turbovec: filtered search dengan allowlist di kernel.
        """
        if len(query) != self.dim:
            raise ValueError(f"Query dim {len(query)} != index dim {self.dim}")

        # Rotate query
        query_norm = self._compute_norm(query)
        query_normalized = self._normalize(query, query_norm)
        query_rotated = self._rotate(query_normalized)

        # Score all vectors (or filtered set)
        candidates = []
        for slot_id, qv in self.vectors.items():
            if allowlist is not None and slot_id not in allowlist:
                continue
            score = self._score_query(query_rotated, qv)
            candidates.append((score, slot_id))

        # Top-k heap (simplified: sort)
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_k = candidates[:min(k, len(candidates))]

        scores = [s for s, _ in top_k]
        indices = [i for _, i in top_k]
        return scores, indices

    def remove(self, slot_id: int) -> bool:
        """Remove vector by slot ID"""
        if slot_id in self.vectors:
            del self.vectors[slot_id]
            return True
        return False

    def write(self, path: str):
        """Persist index to disk"""
        data = {
            "dim": self.dim,
            "bit_width": self.bit_width,
            "next_slot": self.next_slot,
            "total_added": self.total_added,
            "quantizer": {
                "boundaries": self.quantizer.boundaries,
                "centroids": self.quantizer.centroids
            },
            "rotation": ([list(map(float, row)) for row in self.rotation.tolist()]
                         if HAS_NUMPY and hasattr(self.rotation, 'tolist')
                         else self.rotation),
            "vectors": {
                str(sid): {
                    "slot_id": qv.slot_id,
                    "norm": qv.norm,
                    "quantized": base64.b64encode(qv.quantized).decode(),
                    "renormalize_factor": qv.renormalize_factor
                }
                for sid, qv in self.vectors.items()
            }
        }
        with open(path, 'w') as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: str) -> 'TurboQuantIndex':
        """Load index from disk"""
        import base64
        with open(path, 'r') as f:
            data = json.load(f)
        idx = cls(dim=data["dim"], bit_width=data["bit_width"])
        idx.next_slot = data["next_slot"]
        idx.total_added = data["total_added"]
        idx.quantizer.boundaries = data["quantizer"]["boundaries"]
        idx.quantizer.centroids = data["quantizer"]["centroids"]
        idx.rotation = data["rotation"]
        idx.vectors = {
            int(sid): QuantizedVector(
                slot_id=qv["slot_id"],
                norm=qv["norm"],
                quantized=base64.b64decode(qv["quantized"]),
                renormalize_factor=qv["renormalize_factor"],
                original_dim=data["dim"],
                bit_width=data["bit_width"]
            )
            for sid, qv in data["vectors"].items()
        }
        return idx

    def get_stats(self) -> Dict:
        """Index statistics"""
        raw_size = self.total_added * self.dim * 4  # float32
        compressed_size = sum(len(qv.quantized) for qv in self.vectors.values())
        compressed_size += self.total_added * 8  # norm + renormalize (2 floats)
        ratio = raw_size / max(compressed_size, 1)
        return {
            "dim": self.dim,
            "bit_width": self.bit_width,
            "total_vectors": len(self.vectors),
            "raw_size_bytes": raw_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": ratio,
            "levels": self.num_levels
        }


class IdMapIndex:
    """
    TurboQuant index dengan stable external uint64 IDs.
    Tiru turbovec IdMapIndex: O(1) deletion, filtered search.
    """

    def __init__(self, dim: int = 1536, bit_width: int = 4):
        self.index = TurboQuantIndex(dim, bit_width)
        self.id_to_slot: Dict[int, int] = {}  # external_id -> slot_id
        self.slot_to_id: Dict[int, int] = {}  # slot_id -> external_id

    def add_with_ids(self, vectors: List[List[float]], ids: List[int]) -> Dict[int, int]:
        """Add vectors dengan external IDs"""
        if len(vectors) != len(ids):
            raise ValueError("vectors and ids must have same length")
        slot_ids = self.index.add(vectors)
        mapping = {}
        for external_id, slot_id in zip(ids, slot_ids):
            self.id_to_slot[external_id] = slot_id
            self.slot_to_id[slot_id] = external_id
            mapping[external_id] = slot_id
        return mapping

    def search(self, query: List[float], k: int = 10,
               allowlist: Optional[List[int]] = None) -> Tuple[List[float], List[int]]:
        """Search dengan filtered allowlist (external IDs)"""
        slot_allowlist = None
        if allowlist is not None:
            slot_allowlist = {self.id_to_slot.get(eid) for eid in allowlist
                             if eid in self.id_to_slot}
            slot_allowlist.discard(None)
        scores, slot_ids = self.index.search(query, k, slot_allowlist)
        # Convert slot IDs back ke external IDs
        external_ids = [self.slot_to_id.get(sid, sid) for sid in slot_ids]
        return scores, external_ids

    def remove(self, external_id: int) -> bool:
        """O(1) removal by external ID"""
        slot_id = self.id_to_slot.get(external_id)
        if slot_id is None:
            return False
        self.index.remove(slot_id)
        del self.id_to_slot[external_id]
        del self.slot_to_id[slot_id]
        return True

    def write(self, path: str):
        """Persist IdMap index"""
        self.index.write(path + ".idx")
        mapping = {
            "id_to_slot": {str(k): v for k, v in self.id_to_slot.items()},
            "slot_to_id": {str(k): v for k, v in self.slot_to_id.items()}
        }
        with open(path + ".map", 'w') as f:
            json.dump(mapping, f)

    @classmethod
    def load(cls, path: str) -> 'IdMapIndex':
        """Load IdMap index"""
        idx = cls()
        idx.index = TurboQuantIndex.load(path + ".idx")
        with open(path + ".map", 'r') as f:
            mapping = json.load(f)
        idx.id_to_slot = {int(k): v for k, v in mapping["id_to_slot"].items()}
        idx.slot_to_id = {int(k): v for k, v in mapping["slot_to_id"].items()}
        return idx

    def get_stats(self) -> Dict:
        base = self.index.get_stats()
        base["external_ids"] = len(self.id_to_slot)
        return base


class MAGNATRIXVectorStore:
    """
    Integration wrapper untuk MAGNATRIX knowledge layer.
    Connect TurboQuant index dengan existing RAG, memory, dan knowledge graph.
    """

    def __init__(self, dim: int = 1536, bit_width: int = 4):
        self.index = IdMapIndex(dim, bit_width)
        self.documents: Dict[int, Dict] = {}  # external_id -> document metadata
        self._embedder: Optional[Callable] = None

    def set_embedder(self, embed_fn: Callable[[str], List[float]]):
        """Set embedding function (e.g., OpenAI, local model)"""
        self._embedder = embed_fn

    async def index_document(self, doc_id: str, content: str,
                             metadata: Dict = None) -> int:
        """Index document dengan auto-embedding"""
        if self._embedder is None:
            raise ValueError("No embedder set")
        embedding = await self._embedder(content) if asyncio.iscoroutinefunction(self._embedder) else self._embedder(content)
        external_id = hashlib.md5(doc_id.encode()).digest()[:8]
        external_id = struct.unpack('>Q', external_id + b'\x00' * 8)[0]
        self.index.add_with_ids([embedding], [external_id])
        self.documents[external_id] = {
            "doc_id": doc_id,
            "content_preview": content[:200],
            "metadata": metadata or {},
            "indexed_at": time.time()
        }
        return external_id

    def search_documents(self, query_text: str, k: int = 10) -> List[Dict]:
        """Semantic search documents"""
        if self._embedder is None:
            raise ValueError("No embedder set")
        query_emb = self._embedder(query_text)
        scores, ids = self.index.search(query_emb, k)
        results = []
        for score, eid in zip(scores, ids):
            doc = self.documents.get(eid)
            if doc:
                results.append({"score": score, "document": doc})
        return results

    def hybrid_search(self, query_text: str, keyword_filter: str = None,
                      k: int = 10) -> List[Dict]:
        """
        Hybrid search: keyword filter + semantic rerank.
        Tiru turbovec filtered search: allowlist dari keyword match.
        """
        # Stage 1: keyword filter (external system narrows candidates)
        allowlist = None
        if keyword_filter:
            allowlist = [eid for eid, doc in self.documents.items()
                        if keyword_filter.lower() in doc.get("content_preview", "").lower()]
        # Stage 2: dense rerank within candidates
        if self._embedder is None:
            return []
        query_emb = self._embedder(query_text)
        scores, ids = self.index.search(query_emb, k, allowlist=allowlist if allowlist else None)
        results = []
        for score, eid in zip(scores, ids):
            doc = self.documents.get(eid)
            if doc:
                results.append({"score": score, "document": doc})
        return results

    def delete_document(self, doc_id: str) -> bool:
        """Delete document by doc_id"""
        # Find external_id dari doc_id
        for eid, doc in self.documents.items():
            if doc["doc_id"] == doc_id:
                self.index.remove(eid)
                del self.documents[eid]
                return True
        return False

    def get_stats(self) -> Dict:
        return {
            "vectors": self.index.get_stats(),
            "documents": len(self.documents),
            "compression_ratio": self.index.get_stats().get("compression_ratio", 0)
        }


# ==================== DEMONSTRATION ====================

if __name__ == "__main__":
    async def demo():
        print("=" * 60)
        print("MAGNATRIX Native TurboQuant Vector Index Demo")
        print("=" * 60)

        # Create index
        idx = TurboQuantIndex(dim=128, bit_width=4)

        # Generate random vectors
        if HAS_NUMPY:
            vectors = [np.random.randn(128).tolist() for _ in range(1000)]
            query = np.random.randn(128).tolist()
        else:
            vectors = [[random.gauss(0, 1) for _ in range(128)] for _ in range(1000)]
            query = [random.gauss(0, 1) for _ in range(128)]

        # Add vectors
        slot_ids = idx.add(vectors)
        print(f"\nAdded {len(slot_ids)} vectors")

        # Search
        scores, indices = idx.search(query, k=10)
        print(f"Top-10 search completed")
        print(f"Best score: {scores[0]:.4f}, slot: {indices[0]}")

        # Stats
        stats = idx.get_stats()
        print(f"\nIndex Statistics:")
        print(f"  Raw size: {stats['raw_size_bytes']:,} bytes")
        print(f"  Compressed: {stats['compressed_size_bytes']:,} bytes")
        print(f"  Compression ratio: {stats['compression_ratio']:.1f}x")
        print(f"  Bit width: {stats['bit_width']}, Levels: {stats['levels']}")

        # IdMapIndex demo
        print("\n--- IdMapIndex Demo ---")
        id_idx = IdMapIndex(dim=128, bit_width=4)
        ids = list(range(1001, 1101))
        id_idx.add_with_ids(vectors[:100], ids)
        scores, ext_ids = id_idx.search(query, k=5)
        print(f"External IDs returned: {ext_ids}")

        # Remove
        removed = id_idx.remove(1005)
        print(f"Removed ID 1005: {removed}")

        # MAGNATRIXVectorStore demo
        print("\n--- MAGNATRIXVectorStore Demo ---")
        store = MAGNATRIXVectorStore(dim=128, bit_width=4)

        def mock_embed(text: str) -> List[float]:
            # Deterministic mock embedding dari text hash
            h = hashlib.md5(text.encode()).digest()
            return [(h[i % 16] / 255.0 - 0.5) * 2 for i in range(128)]

        store.set_embedder(mock_embed)

        await store.index_document("doc-1", "Machine learning is transforming AI", {"category": "AI"})
        await store.index_document("doc-2", "Deep learning neural networks", {"category": "AI"})
        await store.index_document("doc-3", "Quantum computing applications", {"category": "Physics"})

        results = store.search_documents("artificial intelligence", k=3)
        print(f"Semantic search results: {len(results)}")
        for r in results:
            print(f"  Score: {r['score']:.4f} | {r['document']['doc_id']}: {r['document']['content_preview'][:40]}")

        # Hybrid search
        hybrid = store.hybrid_search("neural networks", keyword_filter="deep")
        print(f"\nHybrid search (keyword=deep): {len(hybrid)} results")

        print(f"\nStore stats: {store.get_stats()}")
        print("\n✓ Demo complete!")

    asyncio.run(demo())
