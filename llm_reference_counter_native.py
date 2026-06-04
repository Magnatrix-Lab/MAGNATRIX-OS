"""Reference Counter — smart pointer style, cyclic detection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto

@dataclass
class RefCountedObject:
    obj_id: str
    data: any
    ref_count: int = 0

class ReferenceCounter:
    def __init__(self):
        self.objects: Dict[str, RefCountedObject] = {}
        self.refs: Dict[str, List[str]] = {}

    def create(self, obj_id: str, data: any) -> RefCountedObject:
        obj = RefCountedObject(obj_id, data, 1)
        self.objects[obj_id] = obj
        self.refs[obj_id] = []
        return obj

    def retain(self, obj_id: str) -> bool:
        obj = self.objects.get(obj_id)
        if obj:
            obj.ref_count += 1
            return True
        return False

    def release(self, obj_id: str) -> bool:
        obj = self.objects.get(obj_id)
        if not obj:
            return False
        obj.ref_count -= 1
        if obj.ref_count <= 0:
            self.objects.pop(obj_id)
            self.refs.pop(obj_id, None)
            return True
        return False

    def add_ref(self, from_id: str, to_id: str):
        if from_id in self.refs:
            self.refs[from_id].append(to_id)
            self.retain(to_id)

    def detect_cycle(self, start_id: str) -> bool:
        visited = set()
        stack = [start_id]
        while stack:
            current = stack.pop()
            if current in visited:
                return True
            visited.add(current)
            for ref in self.refs.get(current, []):
                if ref in self.objects:
                    stack.append(ref)
        return False

    def stats(self) -> Dict:
        return {"objects": len(self.objects), "total_refs": sum(len(v) for v in self.refs.values())}

def run():
    rc = ReferenceCounter()
    rc.create("A", {"value": 1})
    rc.create("B", {"value": 2})
    rc.add_ref("A", "B")
    print("Ref B:", rc.objects["B"].ref_count)
    print("Cycle:", rc.detect_cycle("A"))
    print(rc.stats())

if __name__ == "__main__":
    run()
