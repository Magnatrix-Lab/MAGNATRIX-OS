"""LLM Thread Organizer — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime

class ThreadStatus(Enum):
    ACTIVE = auto()
    ARCHIVED = auto()
    PINNED = auto()
    MERGED = auto()

@dataclass
class Thread:
    id: str
    title: str
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    status: ThreadStatus = ThreadStatus.ACTIVE
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class ThreadOrganizer:
    def __init__(self) -> None:
        self._threads: Dict[str, Thread] = {}

    def create(self, thread_id: str, title: str, parent_id: Optional[str] = None) -> Thread:
        now = datetime.now().isoformat()
        thread = Thread(id=thread_id, title=title, parent_id=parent_id, created_at=now, updated_at=now)
        self._threads[thread_id] = thread
        if parent_id and parent_id in self._threads:
            self._threads[parent_id].children.append(thread_id)
        return thread

    def archive(self, thread_id: str) -> bool:
        thread = self._threads.get(thread_id)
        if thread:
            thread.status = ThreadStatus.ARCHIVED
            return True
        return False

    def pin(self, thread_id: str) -> bool:
        thread = self._threads.get(thread_id)
        if thread:
            thread.status = ThreadStatus.PINNED
            return True
        return False

    def merge(self, source_id: str, target_id: str) -> bool:
        source = self._threads.get(source_id)
        target = self._threads.get(target_id)
        if source and target:
            source.status = ThreadStatus.MERGED
            source.parent_id = target_id
            target.children.append(source_id)
            return True
        return False

    def get_thread_tree(self, root_id: str) -> Dict[str, Any]:
        thread = self._threads.get(root_id)
        if not thread:
            return {}
        return {
            "id": thread.id,
            "title": thread.title,
            "status": thread.status.name,
            "children": [self.get_thread_tree(cid) for cid in thread.children if cid in self._threads]
        }

    def get_roots(self) -> List[Thread]:
        return [t for t in self._threads.values() if t.parent_id is None]

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for t in self._threads.values():
            counts[t.status.name] = counts.get(t.status.name, 0) + 1
        return {"total": len(self._threads), "roots": len(self.get_roots()), "by_status": counts}

def run() -> None:
    print("Thread Organizer test")
    e = ThreadOrganizer()
    e.create("t1", "Main Discussion")
    e.create("t2", "Subtopic A", "t1")
    e.create("t3", "Subtopic B", "t1")
    e.create("t4", "Side Thread")
    e.pin("t1")
    e.merge("t4", "t1")
    print("  Tree: " + str(e.get_thread_tree("t1")))
    print("  Roots: " + str([t.title for t in e.get_roots()]))
    print("  Stats: " + str(e.get_stats()))
    print("Thread Organizer test complete.")

if __name__ == "__main__":
    run()
