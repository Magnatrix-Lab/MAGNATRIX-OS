"""Garbage Collector — reference counting, mark-and-sweep, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum, auto

@dataclass
class GCObject:
    obj_id: str
    refs: List[str] = field(default_factory=list)
    marked: bool = False

class GarbageCollector:
    def __init__(self):
        self.objects: Dict[str, GCObject] = {}
        self.roots: Set[str] = set()

    def add_object(self, obj_id: str, refs: List[str] = None):
        self.objects[obj_id] = GCObject(obj_id, refs or [])

    def add_root(self, obj_id: str):
        self.roots.add(obj_id)

    def mark(self):
        for obj in self.objects.values():
            obj.marked = False
        for root in self.roots:
            self._mark_recursive(root)

    def _mark_recursive(self, obj_id: str):
        obj = self.objects.get(obj_id)
        if not obj or obj.marked:
            return
        obj.marked = True
        for ref in obj.refs:
            self._mark_recursive(ref)

    def sweep(self) -> List[str]:
        collected = []
        for obj_id in list(self.objects.keys()):
            if not self.objects[obj_id].marked:
                collected.append(obj_id)
                del self.objects[obj_id]
        return collected

    def collect(self) -> List[str]:
        self.mark()
        return self.sweep()

    def reference_count(self, obj_id: str) -> int:
        count = 0
        for obj in self.objects.values():
            if obj_id in obj.refs:
                count += 1
        return count

    def stats(self) -> Dict:
        return {"objects": len(self.objects), "roots": len(self.roots)}

def run():
    gc = GarbageCollector()
    gc.add_object("A", ["B"])
    gc.add_object("B", ["C"])
    gc.add_object("C")
    gc.add_object("D")
    gc.add_root("A")
    print("Before:", gc.stats())
    collected = gc.collect()
    print("Collected:", collected)
    print("After:", gc.stats())

if __name__ == "__main__":
    run()
