"""LLM Conversation Memory — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class MemoryRole(Enum):
    USER = auto()
    ASSISTANT = auto()
    SYSTEM = auto()

@dataclass
class MemoryEntry:
    id: str
    role: MemoryRole
    content: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class ConversationMemory:
    def __init__(self, max_entries: int = 100) -> None:
        self.max_entries = max_entries
        self._entries: List[MemoryEntry] = []
        self._index: Dict[str, int] = {}

    def add(self, entry: MemoryEntry) -> None:
        if entry.id in self._index:
            self._entries[self._index[entry.id]] = entry
        else:
            if len(self._entries) >= self.max_entries:
                removed = self._entries.pop(0)
                del self._index[removed.id]
                self._rebuild_index()
            self._index[entry.id] = len(self._entries)
            self._entries.append(entry)

    def _rebuild_index(self) -> None:
        self._index = {e.id: i for i, e in enumerate(self._entries)}

    def get_recent(self, n: int = 5) -> List[MemoryEntry]:
        return self._entries[-n:]

    def get_by_role(self, role: MemoryRole) -> List[MemoryEntry]:
        return [e for e in self._entries if e.role == role]

    def search(self, keyword: str) -> List[MemoryEntry]:
        return [e for e in self._entries if keyword.lower() in e.content.lower()]

    def get_stats(self) -> Dict[str, Any]:
        return {"total": len(self._entries), "by_role": {r.name: sum(1 for e in self._entries if e.role == r) for r in MemoryRole}}

def run() -> None:
    print("Conversation Memory test")
    e = ConversationMemory(max_entries=10)
    e.add(MemoryEntry("m1", MemoryRole.USER, "Hello there", "2024-01-01T10:00:00"))
    e.add(MemoryEntry("m2", MemoryRole.ASSISTANT, "Hi! How can I help?", "2024-01-01T10:00:01"))
    e.add(MemoryEntry("m3", MemoryRole.USER, "What is the weather?", "2024-01-01T10:00:02"))
    e.add(MemoryEntry("m4", MemoryRole.ASSISTANT, "It is sunny today.", "2024-01-01T10:00:03"))
    print("  Recent: " + str([en.id for en in e.get_recent(2)]))
    print("  User entries: " + str([en.id for en in e.get_by_role(MemoryRole.USER)]))
    print("  Stats: " + str(e.get_stats()))
    print("Conversation Memory test complete.")

if __name__ == "__main__":
    run()
