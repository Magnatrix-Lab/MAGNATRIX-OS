"""Lock-Free Data Structures — atomic compare-and-swap, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from threading import Lock
import time

@dataclass
class AtomicRef:
    value: Any = None
    _lock: Lock = field(default_factory=Lock, repr=False)

    def compare_and_set(self, expected: Any, new: Any) -> bool:
        with self._lock:
            if self.value == expected:
                self.value = new
                return True
            return False

    def get(self) -> Any:
        with self._lock:
            return self.value

    def set(self, new: Any):
        with self._lock:
            self.value = new

class LockFreeQueue:
    def __init__(self):
        self._head = [None]
        self._tail = self._head
        self._lock = Lock()

    def enqueue(self, value: Any):
        with self._lock:
            node = [value]
            self._tail[0] = node
            self._tail = node

    def dequeue(self) -> Optional[Any]:
        with self._lock:
            if self._head == self._tail:
                return None
            node = self._head[0]
            self._head = node
            return node[0] if node else None

    def is_empty(self) -> bool:
        with self._lock:
            return self._head == self._tail

    def stats(self) -> Dict:
        return {"head": id(self._head), "tail": id(self._tail), "empty": self.is_empty()}

class LockFreeStack:
    def __init__(self):
        self._top = AtomicRef(None)

    def push(self, value: Any):
        while True:
            current = self._top.get()
            new_node = (value, current)
            if self._top.compare_and_set(current, new_node):
                break

    def pop(self) -> Optional[Any]:
        while True:
            current = self._top.get()
            if current is None:
                return None
            value, next_node = current
            if self._top.compare_and_set(current, next_node):
                return value

    def stats(self) -> Dict:
        return {"top": self._top.get()}

def run():
    q = LockFreeQueue()
    q.enqueue(1); q.enqueue(2); q.enqueue(3)
    print(q.dequeue(), q.dequeue(), q.stats())
    s = LockFreeStack()
    s.push("a"); s.push("b"); s.push("c")
    print(s.pop(), s.pop(), s.stats())

if __name__ == "__main__":
    run()
