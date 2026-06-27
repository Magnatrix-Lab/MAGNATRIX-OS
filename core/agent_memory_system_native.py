#!/usr/bin/env python3
"""
Agent Memory System for MAGNATRIX-OS
====================================
Episodic, semantic, and working memory with auto-consolidation,
similarity retrieval, and temporal decay. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, math, random, re, time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import deque


@dataclass
class MemoryEntry:
    """A single memory entry."""
    entry_id: str
    content: str
    memory_type: str  # "episodic", "semantic", "working"
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    source: str = ""  # module or agent that created this
    associations: List[str] = field(default_factory=list)  # IDs of related memories
    
    def relevance_score(self, query_time: Optional[float] = None) -> float:
        """Calculate relevance score with decay."""
        now = query_time or time.time()
        age_hours = (now - self.timestamp) / 3600
        recency = math.exp(-age_hours / 168)  # 1-week half-life
        access_boost = math.log(self.access_count + 1) * 0.1
        return (self.importance * 0.5 + recency * 0.3 + access_boost * 0.2)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryStore:
    """Base memory store with CRUD operations."""
    
    def __init__(self, max_size: int = 10000) -> None:
        self.memories: Dict[str, MemoryEntry] = {}
        self.max_size = max_size
        self._index: Dict[str, Set[str]] = {}  # tag -> memory IDs
    
    def add(self, entry: MemoryEntry) -> bool:
        if len(self.memories) >= self.max_size:
            self._evict_oldest()
        self.memories[entry.entry_id] = entry
        for tag in entry.tags:
            if tag not in self._index:
                self._index[tag] = set()
            self._index[tag].add(entry.entry_id)
        return True
    
    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        entry = self.memories.get(entry_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = time.time()
        return entry
    
    def search_by_tag(self, tag: str) -> List[MemoryEntry]:
        ids = self._index.get(tag, set())
        return [self.memories[i] for i in ids if i in self.memories]
    
    def search_by_content(self, keyword: str) -> List[MemoryEntry]:
        keyword_lower = keyword.lower()
        results = []
        for entry in self.memories.values():
            if keyword_lower in entry.content.lower():
                results.append(entry)
        return results
    
    def _evict_oldest(self) -> None:
        if not self.memories:
            return
        oldest = min(self.memories.values(), key=lambda e: e.last_accessed)
        self._remove(oldest.entry_id)
    
    def _remove(self, entry_id: str) -> None:
        entry = self.memories.pop(entry_id, None)
        if entry:
            for tag in entry.tags:
                if tag in self._index:
                    self._index[tag].discard(entry_id)
    
    def consolidate(self, threshold_hours: float = 24.0) -> List[MemoryEntry]:
        """Consolidate similar memories into summary."""
        now = time.time()
        groups: Dict[str, List[MemoryEntry]] = {}
        for entry in list(self.memories.values()):
            if entry.memory_type == "episodic" and (now - entry.timestamp) > threshold_hours * 3600:
                key = self._hash_content(entry.content[:100])
                if key not in groups:
                    groups[key] = []
                groups[key].append(entry)
        
        consolidated = []
        for key, entries in groups.items():
            if len(entries) >= 3:
                summary = self._summarize(entries)
                consolidated.append(summary)
                for e in entries:
                    self._remove(e.entry_id)
                self.add(summary)
        return consolidated
    
    def _hash_content(self, content: str) -> str:
        # Simple hash for grouping
        words = sorted(set(re.findall(r'\b\w+\b', content.lower())))
        return "_".join(words[:5])
    
    def _summarize(self, entries: List[MemoryEntry]) -> MemoryEntry:
        contents = [e.content for e in entries]
        summary_text = f"Consolidated {len(entries)} events: " + "; ".join(contents[:3])
        return MemoryEntry(
            entry_id=f"consolidated_{int(time.time())}_{random.randint(1000,9999)}",
            content=summary_text,
            memory_type="semantic",
            importance=max(e.importance for e in entries),
            tags=list(set(tag for e in entries for tag in e.tags)),
            source="memory_consolidation",
        )
    
    def get_stats(self) -> Dict[str, Any]:
        types = {}
        for e in self.memories.values():
            types[e.memory_type] = types.get(e.memory_type, 0) + 1
        return {
            "total": len(self.memories),
            "by_type": types,
            "max_size": self.max_size,
        }


class EpisodicMemory(MemoryStore):
    """Event-based memory with temporal ordering."""
    
    def __init__(self, max_size: int = 5000) -> None:
        super().__init__(max_size)
        self.timeline: deque = deque(maxlen=max_size)
    
    def add(self, entry: MemoryEntry) -> bool:
        entry.memory_type = "episodic"
        self.timeline.append(entry.timestamp)
        return super().add(entry)
    
    def recall_recent(self, hours: float = 24.0) -> List[MemoryEntry]:
        cutoff = time.time() - hours * 3600
        return [e for e in self.memories.values() if e.timestamp >= cutoff]
    
    def recall_sequence(self, start_time: float, end_time: float) -> List[MemoryEntry]:
        return sorted(
            [e for e in self.memories.values() if start_time <= e.timestamp <= end_time],
            key=lambda e: e.timestamp
        )


class SemanticMemory(MemoryStore):
    """Fact-based memory with concept associations."""
    
    def __init__(self, max_size: int = 10000) -> None:
        super().__init__(max_size)
        self.concepts: Dict[str, Set[str]] = {}  # concept -> memory IDs
    
    def add(self, entry: MemoryEntry) -> bool:
        entry.memory_type = "semantic"
        result = super().add(entry)
        # Extract concepts
        words = re.findall(r'\b[A-Z][a-z]+\b', entry.content)
        for word in words:
            if word not in self.concepts:
                self.concepts[word] = set()
            self.concepts[word].add(entry.entry_id)
        return result
    
    def query(self, concept: str) -> List[MemoryEntry]:
        ids = self.concepts.get(concept, set())
        return [self.memories[i] for i in ids if i in self.memories]
    
    def infer(self, concept_a: str, concept_b: str) -> List[MemoryEntry]:
        """Find memories connecting two concepts."""
        ids_a = self.concepts.get(concept_a, set())
        ids_b = self.concepts.get(concept_b, set())
        common = ids_a & ids_b
        return [self.memories[i] for i in common if i in self.memories]


class WorkingMemory(MemoryStore):
    """Short-term memory with limited capacity and fast decay."""
    
    def __init__(self, capacity: int = 7) -> None:
        super().__init__(capacity)
        self.capacity = capacity
        self.decay_rate = 0.1  # per minute
    
    def add(self, entry: MemoryEntry) -> bool:
        entry.memory_type = "working"
        if len(self.memories) >= self.capacity:
            self._evict_oldest()
        return super().add(entry)
    
    def decay(self) -> None:
        """Apply time-based decay to working memory."""
        now = time.time()
        to_remove = []
        for entry in list(self.memories.values()):
            minutes_old = (now - entry.timestamp) / 60
            entry.importance *= math.exp(-self.decay_rate * minutes_old)
            if entry.importance < 0.1:
                to_remove.append(entry.entry_id)
        for entry_id in to_remove:
            self._remove(entry_id)
    
    def get_context(self) -> List[MemoryEntry]:
        """Get current working context."""
        self.decay()
        return sorted(self.memories.values(), key=lambda e: e.last_accessed, reverse=True)


class MemoryRetrieval:
    """Advanced retrieval with similarity and relevance."""
    
    def __init__(self, episodic: EpisodicMemory, semantic: SemanticMemory, working: WorkingMemory) -> None:
        self.episodic = episodic
        self.semantic = semantic
        self.working = working
    
    def retrieve(self, query: str, memory_type: Optional[str] = None, top_k: int = 5) -> List[Tuple[MemoryEntry, float]]:
        """Retrieve most relevant memories."""
        all_results = []
        
        # Search in specified or all memory types
        stores = []
        if memory_type == "episodic" or memory_type is None:
            stores.append(self.episodic)
        if memory_type == "semantic" or memory_type is None:
            stores.append(self.semantic)
        if memory_type == "working" or memory_type is None:
            stores.append(self.working)
        
        for store in stores:
            for entry in store.search_by_content(query):
                score = self._similarity(query, entry.content) * entry.relevance_score()
                all_results.append((entry, score))
        
        # Sort by score and return top_k
        all_results.sort(key=lambda x: x[1], reverse=True)
        return all_results[:top_k]
    
    def _similarity(self, query: str, content: str) -> float:
        """Simple word overlap similarity."""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        if not query_words or not content_words:
            return 0.0
        intersection = query_words & content_words
        union = query_words | content_words
        return len(intersection) / len(union) if union else 0.0
    
    def recall_episode(self, context: str) -> List[MemoryEntry]:
        """Recall episodic memories related to context."""
        results = self.retrieve(context, memory_type="episodic", top_k=10)
        return [r[0] for r in results]
    
    def recall_facts(self, concept: str) -> List[MemoryEntry]:
        """Recall semantic facts about a concept."""
        return self.semantic.query(concept)


class AgentMemory:
    """Top-level agent memory system."""
    
    def __init__(self, agent_id: str = "") -> None:
        self.agent_id = agent_id or f"agent_{int(time.time())}"
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.working = WorkingMemory()
        self.retrieval = MemoryRetrieval(self.episodic, self.semantic, self.working)
        self._memory_counter = 0
    
    def remember_event(self, event: str, importance: float = 0.5, tags: List[str] = None) -> str:
        self._memory_counter += 1
        entry = MemoryEntry(
            entry_id=f"{self.agent_id}_epi_{self._memory_counter}",
            content=event,
            memory_type="episodic",
            importance=importance,
            tags=tags or [],
            source=self.agent_id,
        )
        self.episodic.add(entry)
        return entry.entry_id
    
    def learn_fact(self, fact: str, importance: float = 0.7, tags: List[str] = None) -> str:
        self._memory_counter += 1
        entry = MemoryEntry(
            entry_id=f"{self.agent_id}_sem_{self._memory_counter}",
            content=fact,
            memory_type="semantic",
            importance=importance,
            tags=tags or [],
            source=self.agent_id,
        )
        self.semantic.add(entry)
        return entry.entry_id
    
    def hold_thought(self, thought: str, importance: float = 0.9) -> str:
        self._memory_counter += 1
        entry = MemoryEntry(
            entry_id=f"{self.agent_id}_work_{self._memory_counter}",
            content=thought,
            memory_type="working",
            importance=importance,
            source=self.agent_id,
        )
        self.working.add(entry)
        return entry.entry_id
    
    def recall(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        results = self.retrieval.retrieve(query, top_k=top_k)
        return [{"content": r[0].content, "type": r[0].memory_type, "score": r[1], "timestamp": r[0].timestamp} for r in results]
    
    def consolidate(self) -> List[str]:
        consolidated = self.episodic.consolidate()
        return [c.entry_id for c in consolidated]
    
    def get_working_context(self) -> List[str]:
        return [e.content for e in self.working.get_context()]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "episodic": self.episodic.get_stats(),
            "semantic": self.semantic.get_stats(),
            "working": self.working.get_stats(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
