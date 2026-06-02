"""Agent Memory — Long-term episodic and semantic memory for agents.

Modul ini menyediakan:
- EpisodicMemory untuk store experiences/events
- SemanticMemory untuk store facts/knowledge
- MemoryRetrieval untuk retrieve relevant memories
- MemoryConsolidator untuk merge and compress memories
- AgentMemory untuk unified memory system
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class MemoryType(Enum):
    EPISODIC = auto()
    SEMANTIC = auto()
    PROCEDURAL = auto()


@dataclass
class MemoryEntry:
    """Single memory entry."""
    memory_id: str
    content: str
    memory_type: MemoryType
    importance: float = 1.0
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    associations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0


class EpisodicMemory:
    """Store experiences and events."""

    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self._entries: List[MemoryEntry] = []

    def add(self, content: str, importance: float = 1.0, tags: Optional[List[str]] = None) -> MemoryEntry:
        entry = MemoryEntry(
            memory_id=str(uuid.uuid4())[:12],
            content=content,
            memory_type=MemoryType.EPISODIC,
            importance=importance,
            tags=tags or [],
        )
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries.sort(key=lambda e: e.importance * (1 + e.access_count * 0.1))
            self._entries = self._entries[-self.max_entries:]
        return entry

    def recall(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        query_words = set(query.lower().split())
        scored = []
        for entry in self._entries:
            entry_words = set(entry.content.lower().split()) | set(t.lower() for t in entry.tags)
            overlap = len(query_words & entry_words)
            score = overlap * entry.importance * (1 + entry.access_count * 0.1)
            if overlap > 0:
                scored.append((score, entry))
                entry.access_count += 1
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    def get_recent(self, n: int = 10) -> List[MemoryEntry]:
        return sorted(self._entries, key=lambda e: e.timestamp, reverse=True)[:n]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._entries),
            "total_accesses": sum(e.access_count for e in self._entries),
        }


class SemanticMemory:
    """Store facts and knowledge."""

    def __init__(self):
        self._facts: Dict[str, MemoryEntry] = {}
        self._by_tag: Dict[str, List[str]] = {}

    def add_fact(self, key: str, content: str, tags: Optional[List[str]] = None) -> MemoryEntry:
        entry = MemoryEntry(
            memory_id=str(uuid.uuid4())[:12],
            content=content,
            memory_type=MemoryType.SEMANTIC,
            tags=tags or [],
        )
        self._facts[key] = entry
        for tag in entry.tags:
            self._by_tag.setdefault(tag, []).append(key)
        return entry

    def get_fact(self, key: str) -> Optional[MemoryEntry]:
        fact = self._facts.get(key)
        if fact:
            fact.access_count += 1
        return fact

    def query_by_tag(self, tag: str) -> List[MemoryEntry]:
        keys = self._by_tag.get(tag, [])
        return [self._facts[k] for k in keys if k in self._facts]

    def search(self, query: str) -> List[MemoryEntry]:
        query_lower = query.lower()
        results = []
        for entry in self._facts.values():
            if query_lower in entry.content.lower() or any(query_lower in t.lower() for t in entry.tags):
                results.append(entry)
                entry.access_count += 1
        return results


class MemoryRetrieval:
    """Retrieve relevant memories."""

    def __init__(self, episodic: EpisodicMemory, semantic: SemanticMemory):
        self.episodic = episodic
        self.semantic = semantic

    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[MemoryEntry, float]]:
        episodic_results = self.episodic.recall(query, top_k)
        semantic_results = self.semantic.search(query)
        # Combine and score
        all_results = []
        for e in episodic_results:
            all_results.append((e, e.importance * 1.2))  # Boost episodic
        for e in semantic_results:
            all_results.append((e, e.importance * 1.0))
        all_results.sort(key=lambda x: x[1], reverse=True)
        return all_results[:top_k]

    def retrieve_multi(self, queries: List[str], top_k: int = 5) -> Dict[str, List[Tuple[MemoryEntry, float]]]:
        return {q: self.retrieve(q, top_k) for q in queries}


class MemoryConsolidator:
    """Merge and compress memories."""

    def consolidate(self, entries: List[MemoryEntry]) -> MemoryEntry:
        # Merge similar memories into one summary
        combined_content = " | ".join(e.content[:100] for e in entries)
        avg_importance = sum(e.importance for e in entries) / len(entries)
        all_tags = set()
        for e in entries:
            all_tags.update(e.tags)
        return MemoryEntry(
            memory_id=str(uuid.uuid4())[:12],
            content=f"Consolidated: {combined_content[:300]}...",
            memory_type=MemoryType.SEMANTIC,
            importance=avg_importance,
            tags=list(all_tags),
        )

    def compress(self, episodic: EpisodicMemory, threshold: int = 50) -> int:
        if len(episodic._entries) < threshold:
            return 0
        # Group by time window and consolidate
        sorted_entries = sorted(episodic._entries, key=lambda e: e.timestamp)
        groups = [sorted_entries[i:i+5] for i in range(0, len(sorted_entries), 5)]
        new_entries = []
        for group in groups:
            if len(group) > 1:
                consolidated = self.consolidate(group)
                new_entries.append(consolidated)
            else:
                new_entries.append(group[0])
        count = len(episodic._entries)
        episodic._entries = new_entries
        return count - len(new_entries)


class AgentMemory:
    """Unified memory system for agents."""

    def __init__(self, max_episodic: int = 1000):
        self.episodic = EpisodicMemory(max_episodic)
        self.semantic = SemanticMemory()
        self.retrieval = MemoryRetrieval(self.episodic, self.semantic)
        self.consolidator = MemoryConsolidator()
        self._procedural: Dict[str, str] = {}  # skill -> steps

    def remember_experience(self, content: str, importance: float = 1.0, tags: Optional[List[str]] = None) -> MemoryEntry:
        return self.episodic.add(content, importance, tags)

    def learn_fact(self, key: str, content: str, tags: Optional[List[str]] = None) -> MemoryEntry:
        return self.semantic.add_fact(key, content, tags)

    def learn_skill(self, skill_name: str, steps: str) -> None:
        self._procedural[skill_name] = steps

    def recall(self, query: str, top_k: int = 5) -> List[Tuple[MemoryEntry, float]]:
        return self.retrieval.retrieve(query, top_k)

    def consolidate(self) -> int:
        return self.consolidator.compress(self.episodic)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "episodic": self.episodic.get_stats(),
            "semantic_facts": len(self.semantic._facts),
            "procedural_skills": len(self._procedural),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "episodic": len(self.episodic._entries),
                "semantic": len(self.semantic._facts),
                "procedural": list(self._procedural.keys()),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("AGENT MEMORY DEMO")
    print("=" * 70)

    memory = AgentMemory(max_episodic=100)

    # 1. Learn facts
    print("\n[1] Learn Facts")
    memory.learn_fact("python", "Python is a programming language", ["coding", "language"])
    memory.learn_fact("ai", "AI stands for Artificial Intelligence", ["ai", "concept"])
    memory.learn_fact("paris", "Paris is the capital of France", ["geography", "city"])
    print(f"  Facts learned: {len(memory.semantic._facts)}")

    # 2. Remember experiences
    print("\n[2] Remember Experiences")
    memory.remember_experience("Helped user debug Python code", importance=0.8, tags=["coding", "help"])
    memory.remember_experience("Explained neural networks to user", importance=0.9, tags=["ai", "teaching"])
    memory.remember_experience("Fixed a SQL query", importance=0.7, tags=["coding", "database"])
    print(f"  Experiences: {len(memory.episodic._entries)}")

    # 3. Recall
    print("\n[3] Recall Memories")
    results = memory.recall("Python programming", top_k=3)
    print(f"  Query: 'Python programming'")
    for entry, score in results:
        print(f"    [{score:.2f}] {entry.content[:50]}... ({entry.memory_type.name})")

    # 4. Query by tag
    print("\n[4] Query by Tag")
    coding_facts = memory.semantic.query_by_tag("coding")
    print(f"  Coding facts: {len(coding_facts)}")
    for f in coding_facts:
        print(f"    {f.content}")

    # 5. Learn skill
    print("\n[5] Learn Procedural Skill")
    memory.learn_skill("debug_python", "1. Read error message\n2. Check line numbers\n3. Verify syntax\n4. Test fix")
    print(f"  Skills: {list(memory._procedural.keys())}")
    print(f"  Debug steps:\n    {memory._procedural['debug_python']}")

    # 6. Consolidation
    print("\n[6] Memory Consolidation")
    for i in range(20):
        memory.remember_experience(f"Experience {i}: helped with task", importance=0.5)
    before = len(memory.episodic._entries)
    compressed = memory.consolidate()
    after = len(memory.episodic._entries)
    print(f"  Before: {before}, After: {after}, Compressed: {compressed}")

    # 7. Stats
    print(f"\n[7] Stats")
    print(f"  {memory.get_stats()}")

    # 8. Export
    print("\n[8] Export")
    memory.export("/tmp/agent_memory.json")
    print("  Exported to /tmp/agent_memory.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
