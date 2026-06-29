
"""
typed_semantic_memory_native.py
MAGNATRIX-OS — Typed Semantic Memory Store

Inspired by Memanto (moorcheh-ai/memanto):
Typed semantic memory with 13 categories and zero-ingestion-latency storage.
Information-theoretic retrieval without vector databases.

Pure Python standard library.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto


class MemoryType(Enum):
    INSTRUCTION = "instruction"
    FACT = "fact"
    DECISION = "decision"
    GOAL = "goal"
    COMMITMENT = "commitment"
    PREFERENCE = "preference"
    RELATIONSHIP = "relationship"
    CONTEXT = "context"
    EVENT = "event"
    LEARNING = "learning"
    OBSERVATION = "observation"
    ARTIFACT = "artifact"
    ERROR = "error"


@dataclass
class MemoryEntry:
    memory_id: str
    content: str
    memory_type: str
    created_at: str
    updated_at: str
    confidence: float = 1.0
    provenance: str = "explicit"
    tags: List[str] = field(default_factory=list)
    version: int = 1
    agent_id: str = "default"
    session_id: str = ""
    expires_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


class TypedSemanticMemoryStore:
    """Typed semantic memory store with zero ingestion latency."""

    def __init__(self, memory_file: str = "semantic_memory.json"):
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memories: Dict[str, MemoryEntry] = {}
        self._type_index: Dict[str, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._agent_index: Dict[str, Set[str]] = {}
        self._load()

    def _load(self) -> None:
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for mid, md in data.items():
                        self.memories[mid] = MemoryEntry(**md)
                self._rebuild_indexes()
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump({mid: asdict(m) for mid, m in self.memories.items()}, f, indent=2)

    def _rebuild_indexes(self) -> None:
        self._type_index = {}
        self._tag_index = {}
        self._agent_index = {}
        for mid, m in self.memories.items():
            self._type_index.setdefault(m.memory_type, set()).add(mid)
            for tag in m.tags:
                self._tag_index.setdefault(tag, set()).add(mid)
            self._agent_index.setdefault(m.agent_id, set()).add(mid)

    def _generate_id(self, content: str) -> str:
        return hashlib.sha256(f"{content}:{datetime.now().timestamp()}".encode()).hexdigest()[:16]

    def remember(self, content: str, memory_type: str = "fact", confidence: float = 1.0,
                 provenance: str = "explicit", tags: Optional[List[str]] = None,
                 agent_id: str = "default", session_id: str = "") -> MemoryEntry:
        """Store a memory with zero ingestion latency."""
        mid = self._generate_id(content)
        entry = MemoryEntry(
            memory_id=mid, content=content, memory_type=memory_type,
            confidence=confidence, provenance=provenance,
            tags=tags or [], agent_id=agent_id, session_id=session_id,
            created_at=datetime.now().isoformat(), updated_at=datetime.now().isoformat(),
        )
        self.memories[mid] = entry
        self._rebuild_indexes()
        self._save()
        return entry

    def recall(self, query: str, memory_type: Optional[str] = None,
               tags: Optional[List[str]] = None, agent_id: Optional[str] = None,
               limit: int = 10) -> List[MemoryEntry]:
        """Information-theoretic retrieval - exact match + keyword scoring."""
        candidates = set(self.memories.keys())
        # Filter by type
        if memory_type:
            candidates &= self._type_index.get(memory_type, set())
        # Filter by tags
        if tags:
            tag_matches = set()
            for tag in tags:
                tag_matches |= self._tag_index.get(tag, set())
            candidates &= tag_matches
        # Filter by agent
        if agent_id:
            candidates &= self._agent_index.get(agent_id, set())
        # Score by keyword overlap
        query_words = set(query.lower().split())
        scored = []
        for mid in candidates:
            m = self.memories[mid]
            content_words = set(m.content.lower().split())
            overlap = len(query_words & content_words)
            score = overlap / max(len(query_words), 1)
            # Boost by confidence and recency
            try:
                age_days = (datetime.now() - datetime.fromisoformat(m.created_at)).days
                recency_boost = max(0, 1 - age_days / 365)
            except Exception:
                recency_boost = 0.5
            final_score = score * m.confidence * (0.5 + 0.5 * recency_boost)
            scored.append((final_score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]

    def answer(self, query: str, memory_type: Optional[str] = None,
               context_size: int = 5) -> Dict[str, Any]:
        """Generate RAG-style answer from retrieved memory."""
        relevant = self.recall(query, memory_type, limit=context_size)
        if not relevant:
            return {"answer": "", "sources": [], "confidence": 0.0}
        # Build answer from memory context
        context_parts = []
        for i, m in enumerate(relevant, 1):
            context_parts.append(f"[{i}] {m.content}")
        context = "\n".join(context_parts)
        # Simple answer synthesis (in real implementation, this would use LLM)
        answer = f"Based on {len(relevant)} memory entries:\n{context}"
        avg_confidence = sum(m.confidence for m in relevant) / len(relevant)
        return {
            "answer": answer,
            "sources": [{"id": m.memory_id, "type": m.memory_type, "content": m.content[:100]} for m in relevant],
            "confidence": avg_confidence,
        }

    def forget(self, memory_id: str) -> bool:
        if memory_id in self.memories:
            del self.memories[memory_id]
            self._rebuild_indexes()
            self._save()
            return True
        return False

    def update(self, memory_id: str, content: Optional[str] = None,
               confidence: Optional[float] = None) -> Optional[MemoryEntry]:
        if memory_id not in self.memories:
            return None
        m = self.memories[memory_id]
        if content:
            m.content = content
        if confidence is not None:
            m.confidence = confidence
        m.version += 1
        m.updated_at = datetime.now().isoformat()
        self._save()
        return m

    def get_by_type(self, memory_type: str) -> List[MemoryEntry]:
        return [self.memories[mid] for mid in self._type_index.get(memory_type, set()) if mid in self.memories]

    def get_stats(self) -> Dict[str, Any]:
        type_counts = {t: len(s) for t, s in self._type_index.items()}
        return {
            "total_memories": len(self.memories),
            "type_breakdown": type_counts,
            "total_agents": len(self._agent_index),
            "total_tags": len(self._tag_index),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TypedSemanticMemoryStore", "MemoryEntry", "MemoryType"]
