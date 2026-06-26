#!/usr/bin/env python3
"""Long-term Memory for MAGNATRIX-OS — Vector-based episodic memory with retrieval."""
from __future__ import annotations
import json, re, time, threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class MemoryEntry:
    id: str
    content: str
    embedding: List[float] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    importance: float = 1.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class LongTermMemory:
    def __init__(self, store_dir: str = "./data/memory") -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._entries: List[MemoryEntry] = []
        self._lock = threading.Lock()
        self._id_counter = 0

    def _simple_embed(self, text: str) -> List[float]:
        text = text.lower()
        vec = [0.0] * 64
        for i, c in enumerate(text[:64]):
            vec[i] = ord(c) / 256.0
        norm = sum(v*v for v in vec) ** 0.5 or 1
        return [v/norm for v in vec]

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        return sum(x*y for x,y in zip(a,b))

    def store(self, content: str, importance: float = 1.0, tags: List[str] = None) -> str:
        with self._lock:
            self._id_counter += 1
            entry = MemoryEntry(
                id=f"mem_{self._id_counter}",
                content=content,
                embedding=self._simple_embed(content),
                importance=importance,
                tags=tags or [],
            )
            self._entries.append(entry)
            return entry.id

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        q_emb = self._simple_embed(query)
        with self._lock:
            scored = []
            for e in self._entries:
                score = self._cosine_sim(q_emb, e.embedding) * e.importance
                scored.append((score, e))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [{"id": e.id, "content": e.content[:200], "score": round(s, 4), "tags": e.tags} for s, e in scored[:top_k]]

    def save(self) -> str:
        path = self.store_dir / "memory.json"
        data = [{"id": e.id, "content": e.content, "ts": e.timestamp, "importance": e.importance, "tags": e.tags} for e in self._entries]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return str(path)

    def stats(self) -> Dict[str, Any]:
        return {"entries": len(self._entries), "store_dir": str(self.store_dir)}
