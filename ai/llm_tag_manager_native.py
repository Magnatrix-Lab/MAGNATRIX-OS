"""LLM Tag Manager — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

@dataclass
class Tag:
    id: str
    name: str
    color: str = "#000000"
    metadata: Dict[str, Any] = field(default_factory=dict)

class TagManager:
    def __init__(self) -> None:
        self._tags: Dict[str, Tag] = {}
        self._tagged: Dict[str, Set[str]] = {}
        self._reverse: Dict[str, Set[str]] = {}

    def create_tag(self, tag: Tag) -> None:
        self._tags[tag.id] = tag

    def tag(self, item_id: str, tag_id: str) -> None:
        if tag_id not in self._tags:
            return
        if item_id not in self._tagged:
            self._tagged[item_id] = set()
        self._tagged[item_id].add(tag_id)
        if tag_id not in self._reverse:
            self._reverse[tag_id] = set()
        self._reverse[tag_id].add(item_id)

    def untag(self, item_id: str, tag_id: str) -> None:
        if item_id in self._tagged:
            self._tagged[item_id].discard(tag_id)
        if tag_id in self._reverse:
            self._reverse[tag_id].discard(item_id)

    def get_tags(self, item_id: str) -> List[Tag]:
        tag_ids = self._tagged.get(item_id, set())
        return [self._tags[tid] for tid in tag_ids if tid in self._tags]

    def get_items(self, tag_id: str) -> List[str]:
        return list(self._reverse.get(tag_id, set()))

    def has_tag(self, item_id: str, tag_id: str) -> bool:
        return tag_id in self._tagged.get(item_id, set())

    def get_stats(self) -> Dict[str, Any]:
        return {"tags": len(self._tags), "tagged_items": len(self._tagged), "total_taggings": sum(len(t) for t in self._tagged.values())}

def run() -> None:
    print("Tag Manager test")
    e = TagManager()
    e.create_tag(Tag("t1", "important", "#FF0000"))
    e.create_tag(Tag("t2", "draft", "#FFFF00"))
    e.create_tag(Tag("t3", "reviewed", "#00FF00"))
    e.tag("doc1", "t1")
    e.tag("doc1", "t2")
    e.tag("doc2", "t1")
    e.tag("doc3", "t3")
    print("  doc1 tags: " + str([t.name for t in e.get_tags("doc1")]))
    print("  important items: " + str(e.get_items("t1")))
    print("  doc1 has important: " + str(e.has_tag("doc1", "t1")))
    e.untag("doc1", "t2")
    print("  After untag doc1 tags: " + str([t.name for t in e.get_tags("doc1")]))
    print("  Stats: " + str(e.get_stats()))
    print("Tag Manager test complete.")

if __name__ == "__main__":
    run()
