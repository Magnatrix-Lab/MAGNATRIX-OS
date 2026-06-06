#!/usr/bin/env python3
"""
Context Manager for MAGNATRIX-OS
Long-term memory, context window management, and lightweight vector search
for conversation history, knowledge fragments, and session state.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class MemoryType(enum.Enum):
    """Classification of stored context fragment."""
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"
    FACT = "fact"
    PREFERENCE = "preference"
    SESSION = "session"
    TOOL_RESULT = "tool_result"
    ERROR = "error"


class RetentionPolicy(enum.Enum):
    """How long a memory fragment should be retained."""
    EPHEMERAL = "ephemeral"      # session only
    SHORT = "short"              # hours
    MEDIUM = "medium"            # days
    LONG = "long"                # weeks
    PERMANENT = "permanent"      # until deleted


@dataclasses.dataclass
class MemoryFragment:
    """A single unit of context memory."""
    fragment_id: str
    content: str
    memory_type: MemoryType
    retention: RetentionPolicy
    source: str  # module, user, tool, etc.
    created_at: float
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    tags: Set[str] = dataclasses.field(default_factory=set)
    access_count: int = 0
    last_accessed: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fragment_id": self.fragment_id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "retention": self.retention.value,
            "source": self.source,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
            "tags": sorted(self.tags),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }


class ContextManager:
    """In-memory + disk-backed context manager with vector search simulation."""

    def __init__(self, storage_dir: Optional[str] = None, max_context_tokens: int = 8000) -> None:
        self.storage_dir = Path(storage_dir) if storage_dir else Path("/tmp/magnatrix_context")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_tokens = max_context_tokens
        self._fragments: Dict[str, MemoryFragment] = {}
        self._index_path = self.storage_dir / "context_index.json"
        self._load()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    frag = MemoryFragment(
                        fragment_id=item["fragment_id"],
                        content=item["content"],
                        memory_type=MemoryType(item["memory_type"]),
                        retention=RetentionPolicy(item["retention"]),
                        source=item["source"],
                        created_at=item["created_at"],
                        expires_at=item.get("expires_at"),
                        metadata=item.get("metadata", {}),
                        tags=set(item.get("tags", [])),
                        access_count=item.get("access_count", 0),
                        last_accessed=item.get("last_accessed"),
                    )
                    self._fragments[frag.fragment_id] = frag
            except Exception:
                pass

    def _save(self) -> None:
        data = [f.to_dict() for f in self._fragments.values()]
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _generate_id(self, content: str) -> str:
        return hashlib.sha256((content + str(time.time())).encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        retention: RetentionPolicy = RetentionPolicy.MEDIUM,
        source: str = "user",
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_seconds: Optional[int] = None,
    ) -> MemoryFragment:
        frag_id = self._generate_id(content)
        now = time.time()
        frag = MemoryFragment(
            fragment_id=frag_id,
            content=content,
            memory_type=memory_type,
            retention=retention,
            source=source,
            created_at=now,
            expires_at=now + expires_in_seconds if expires_in_seconds else self._default_expiry(retention, now),
            metadata=metadata or {},
            tags=tags or set(),
        )
        self._fragments[frag_id] = frag
        self._save()
        return frag

    def _default_expiry(self, retention: RetentionPolicy, now: float) -> Optional[float]:
        mapping = {
            RetentionPolicy.EPHEMERAL: 3600,
            RetentionPolicy.SHORT: 86400,
            RetentionPolicy.MEDIUM: 604800,
            RetentionPolicy.LONG: 2592000,
            RetentionPolicy.PERMANENT: None,
        }
        seconds = mapping.get(retention)
        return now + seconds if seconds else None

    def retrieve(self, fragment_id: str) -> Optional[MemoryFragment]:
        frag = self._fragments.get(fragment_id)
        if frag:
            frag.access_count += 1
            frag.last_accessed = time.time()
            self._save()
        return frag

    def delete(self, fragment_id: str) -> bool:
        if fragment_id in self._fragments:
            del self._fragments[fragment_id]
            self._save()
            return True
        return False

    def update(self, fragment_id: str, content: Optional[str] = None, tags: Optional[Set[str]] = None) -> bool:
        frag = self._fragments.get(fragment_id)
        if not frag:
            return False
        if content is not None:
            frag.content = content
        if tags is not None:
            frag.tags = tags
        self._save()
        return True

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, keyword: str, memory_type: Optional[MemoryType] = None, limit: int = 10) -> List[MemoryFragment]:
        """Keyword search with optional type filtering."""
        kw = keyword.lower()
        results = []
        for frag in self._fragments.values():
            if self._is_expired(frag):
                continue
            if memory_type and frag.memory_type != memory_type:
                continue
            if kw in frag.content.lower() or any(kw in t.lower() for t in frag.tags):
                results.append(frag)
        results.sort(key=lambda f: f.access_count + (1 if f.last_accessed else 0), reverse=True)
        return results[:limit]

    def search_similar(self, content: str, limit: int = 10) -> List[Tuple[MemoryFragment, float]]:
        """Simulated vector search using token overlap / Jaccard similarity."""
        query_tokens = set(content.lower().split())
        scored: List[Tuple[MemoryFragment, float]] = []
        for frag in self._fragments.values():
            if self._is_expired(frag):
                continue
            frag_tokens = set(frag.content.lower().split())
            if not frag_tokens:
                continue
            intersection = query_tokens & frag_tokens
            union = query_tokens | frag_tokens
            score = len(intersection) / len(union) if union else 0.0
            if score > 0.1:
                scored.append((frag, round(score, 3)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def get_by_type(self, memory_type: MemoryType) -> List[MemoryFragment]:
        return [f for f in self._fragments.values() if f.memory_type == memory_type and not self._is_expired(f)]

    def get_by_source(self, source: str) -> List[MemoryFragment]:
        return [f for f in self._fragments.values() if f.source == source and not self._is_expired(f)]

    def get_by_tag(self, tag: str) -> List[MemoryFragment]:
        return [f for f in self._fragments.values() if tag in f.tags and not self._is_expired(f)]

    def get_recent(self, count: int = 10) -> List[MemoryFragment]:
        sorted_frags = sorted(
            (f for f in self._fragments.values() if not self._is_expired(f)),
            key=lambda f: f.created_at,
            reverse=True,
        )
        return sorted_frags[:count]

    # ------------------------------------------------------------------
    # Context window management
    # ------------------------------------------------------------------

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate: 1 token ~ 4 chars for English/mixed."""
        return len(text) // 4

    def build_context(self, query: str, max_tokens: Optional[int] = None) -> str:
        """Build a context string from relevant memories within token budget."""
        budget = max_tokens or self.max_tokens
        # Start with most similar fragments
        similar = self.search_similar(query, limit=50)
        included: List[MemoryFragment] = []
        token_used = 0
        for frag, _ in similar:
            frag_tokens = self._estimate_tokens(frag.content)
            if token_used + frag_tokens > budget:
                break
            included.append(frag)
            token_used += frag_tokens
        # Add recent conversations to fill remaining budget
        if token_used < budget:
            recent = self.get_recent(20)
            for frag in recent:
                if frag in included:
                    continue
                frag_tokens = self._estimate_tokens(frag.content)
                if token_used + frag_tokens > budget:
                    break
                included.append(frag)
                token_used += frag_tokens
        # Sort by creation time for coherent narrative
        included.sort(key=lambda f: f.created_at)
        return "\n---\n".join(f"[{f.memory_type.value}] {f.source}: {f.content}" for f in included)

    def clear_context(self, memory_type: Optional[MemoryType] = None) -> int:
        """Clear all or specific type of memory."""
        if memory_type is None:
            count = len(self._fragments)
            self._fragments.clear()
        else:
            to_remove = [fid for fid, f in self._fragments.items() if f.memory_type == memory_type]
            count = len(to_remove)
            for fid in to_remove:
                del self._fragments[fid]
        self._save()
        return count

    def _is_expired(self, frag: MemoryFragment) -> bool:
        if frag.expires_at is None:
            return False
        return time.time() > frag.expires_at

    def prune_expired(self) -> int:
        """Remove expired fragments."""
        expired = [fid for fid, f in self._fragments.items() if self._is_expired(f)]
        for fid in expired:
            del self._fragments[fid]
        if expired:
            self._save()
        return len(expired)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        by_type: Dict[str, int] = {}
        by_retention: Dict[str, int] = {}
        total_tokens = 0
        expired = 0
        for f in self._fragments.values():
            by_type[f.memory_type.value] = by_type.get(f.memory_type.value, 0) + 1
            by_retention[f.retention.value] = by_retention.get(f.retention.value, 0) + 1
            total_tokens += self._estimate_tokens(f.content)
            if self._is_expired(f):
                expired += 1
        return {
            "total_fragments": len(self._fragments),
            "by_type": by_type,
            "by_retention": by_retention,
            "estimated_tokens": total_tokens,
            "expired_fragments": expired,
            "storage_dir": str(self.storage_dir),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="magnatrix_ctx_")
    ctx = ContextManager(tmp, max_context_tokens=2000)
    print("=== Context Manager Demo ===\n")
    # Store various memories
    ctx.store("User asked about Python best practices", MemoryType.CONVERSATION, source="user", tags={"python"})
    ctx.store("PEP 8 recommends 4 spaces for indentation", MemoryType.KNOWLEDGE, retention=RetentionPolicy.PERMANENT, source="system", tags={"python", "pep8"})
    ctx.store("User prefers dark mode UI", MemoryType.PREFERENCE, retention=RetentionPolicy.LONG, source="user", tags={"ui", "preference"})
    ctx.store("Result: 42", MemoryType.TOOL_RESULT, source="calculator", tags={"math"})
    ctx.store("Error: division by zero", MemoryType.ERROR, source="calculator", tags={"math", "error"})
    print(f"Stored {len(ctx._fragments)} fragments")
    # Search
    print(f"\nSearch 'python': {[f.content[:40] for f in ctx.search('python')]}")
    # Similarity
    similar = ctx.search_similar("What are Python coding standards?", limit=3)
    print(f"\nSimilar to 'Python coding standards':")
    for frag, score in similar:
        print(f"  [{score:.2f}] {frag.content[:50]}")
    # Build context
    context = ctx.build_context("Tell me about Python style")
    print(f"\nBuilt context ({len(context)} chars):")
    print(context[:500])
    # Stats
    print(f"\nStats: {ctx.stats()}")
    # Cleanup
    import shutil
    shutil.rmtree(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
