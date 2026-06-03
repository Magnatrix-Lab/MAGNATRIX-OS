"""LLM Registry Hub — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class RegistryEntryType(Enum):
    MODEL = auto()
    MODULE = auto()
    SERVICE = auto()
    PLUGIN = auto()

@dataclass
class RegistryEntry:
    id: str
    name: str
    entry_type: RegistryEntryType
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

class RegistryHub:
    def __init__(self) -> None:
        self._entries: Dict[str, RegistryEntry] = {}
        self._by_type: Dict[RegistryEntryType, List[str]] = {}
        self._by_tag: Dict[str, List[str]] = {}

    def register(self, entry: RegistryEntry) -> None:
        self._entries[entry.id] = entry
        if entry.entry_type not in self._by_type:
            self._by_type[entry.entry_type] = []
        if entry.id not in self._by_type[entry.entry_type]:
            self._by_type[entry.entry_type].append(entry.id)
        for tag in entry.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = []
            if entry.id not in self._by_tag[tag]:
                self._by_tag[tag].append(entry.id)

    def unregister(self, entry_id: str) -> bool:
        entry = self._entries.pop(entry_id, None)
        if entry:
            if entry.entry_type in self._by_type:
                self._by_type[entry.entry_type] = [eid for eid in self._by_type[entry.entry_type] if eid != entry_id]
            for tag in entry.tags:
                if tag in self._by_tag:
                    self._by_tag[tag] = [eid for eid in self._by_tag[tag] if eid != entry_id]
            return True
        return False

    def get(self, entry_id: str) -> Optional[RegistryEntry]:
        return self._entries.get(entry_id)

    def find_by_type(self, entry_type: RegistryEntryType) -> List[RegistryEntry]:
        ids = self._by_type.get(entry_type, [])
        return [self._entries[eid] for eid in ids if eid in self._entries]

    def find_by_tag(self, tag: str) -> List[RegistryEntry]:
        ids = self._by_tag.get(tag, [])
        return [self._entries[eid] for eid in ids if eid in self._entries]

    def get_stats(self) -> Dict[str, Any]:
        return {"entries": len(self._entries), "by_type": {t.name: len(ids) for t, ids in self._by_type.items()}, "tags": len(self._by_tag)}

def run() -> None:
    print("Registry Hub test")
    e = RegistryHub()
    e.register(RegistryEntry("m1", "GPT-4", RegistryEntryType.MODEL, "4.0", tags=["llm", "openai"]))
    e.register(RegistryEntry("m2", "Claude", RegistryEntryType.MODEL, "3.0", tags=["llm", "anthropic"]))
    e.register(RegistryEntry("s1", "EmbeddingService", RegistryEntryType.SERVICE, "1.0", tags=["embedding"]))
    print("  Models: " + str([en.name for en in e.find_by_type(RegistryEntryType.MODEL)]))
    print("  LLM tagged: " + str([en.name for en in e.find_by_tag("llm")]))
    print("  Stats: " + str(e.get_stats()))
    print("Registry Hub test complete.")

if __name__ == "__main__":
    run()
