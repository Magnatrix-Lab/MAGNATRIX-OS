#!/usr/bin/env python3
"""
vector_memory_native.py
MAGNATRIX-OS — Native Vector Memory (Hippocampus Layer)

In-memory vector database with cosine similarity, L2 distance, optional disk persistence.
Chunking, metadata filtering, top-k retrieval. Pure stdlib — no numpy.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class VectorEntry:
    """A single vector entry with metadata."""
    id: str
    vector: List[float]
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class VectorMemoryNative:
    """
    Native vector memory store — pure Python stdlib, no numpy.
    Supports cosine similarity, L2 distance, metadata filtering, top-k.
    """

    def __init__(self, workspace: str = "./vector_memory", dims: int = 384) -> None:
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.dims = dims
        self._entries: Dict[str, VectorEntry] = {}
        self._lock = threading.RLock()
        self._index_path = self.workspace / "vectors.json"
        self._load()

    def _load(self) -> None:
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for eid, ed in data.items():
                    self._entries[eid] = VectorEntry(**ed)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump({eid: asdict(e) for eid, e in self._entries.items()}, f, indent=2)

    def _l2_normalize(self, vec: List[float]) -> List[float]:
        mag = math.sqrt(sum(v * v for v in vec))
        if mag == 0:
            return [0.0] * len(vec)
        return [v / mag for v in vec]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        a_norm = self._l2_normalize(a)
        b_norm = self._l2_normalize(b)
        return sum(x * y for x, y in zip(a_norm, b_norm))

    def _l2_distance(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def _hash_text(self, text: str) -> List[float]:
        """Simple deterministic text-to-vector for stdlib environments."""
        # Simple bag-of-words-style hash vector
        import hashlib
        vec = [0.0] * self.dims
        words = text.lower().split()
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            for i in range(self.dims):
                vec[i] += ((h >> (i % 32)) & 1) * 2 - 1
        return self._l2_normalize(vec)

    def add(self, text: str, vector: Optional[List[float]] = None,
            metadata: Optional[Dict[str, Any]] = None, entry_id: Optional[str] = None) -> str:
        """Add a text entry. Auto-generates vector if not provided."""
        with self._lock:
            eid = entry_id or f"vec_{int(time.time() * 1000)}_{len(self._entries)}"
            vec = vector or self._hash_text(text)
            entry = VectorEntry(
                id=eid, vector=vec, text=text,
                metadata=metadata or {}, timestamp=time.time()
            )
            self._entries[eid] = entry
            self._save()
            return eid

    def search(self, query: str, top_k: int = 5,
               metric: str = "cosine", filters: Optional[Dict[str, Any]] = None) -> List[Tuple[float, VectorEntry]]:
        """Search entries by query text. Returns (score, entry) sorted."""
        with self._lock:
            query_vec = self._hash_text(query)
            candidates = []
            for entry in self._entries.values():
                if filters and not self._matches_filters(entry, filters):
                    continue
                if metric == "cosine":
                    score = self._cosine_similarity(query_vec, entry.vector)
                elif metric == "l2":
                    score = -self._l2_distance(query_vec, entry.vector)  # negate for sorting
                else:
                    score = self._cosine_similarity(query_vec, entry.vector)
                candidates.append((score, entry))
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[:top_k]

    def _matches_filters(self, entry: VectorEntry, filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            if key not in entry.metadata:
                return False
            if isinstance(value, list):
                if entry.metadata[key] not in value:
                    return False
            elif entry.metadata[key] != value:
                return False
        return True

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            if entry_id in self._entries:
                del self._entries[entry_id]
                self._save()
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "entries": len(self._entries),
                "dims": self.dims,
                "workspace": str(self.workspace),
                "persisted": self._index_path.exists(),
            }

    def export(self, path: Optional[str] = None) -> str:
        """Export all entries to JSON."""
        export_path = Path(path) if path else self.workspace / f"export_{int(time.time())}.json"
        with self._lock:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump({eid: asdict(e) for eid, e in self._entries.items()}, f, indent=2)
        return str(export_path)

    def import_(self, path: str) -> int:
        """Import entries from JSON."""
        with self._lock:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = 0
            for eid, ed in data.items():
                self._entries[eid] = VectorEntry(**ed)
                count += 1
            self._save()
            return count
