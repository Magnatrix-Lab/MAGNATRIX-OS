"""Priority Queue - Heap-based priority queue for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import heapq

@dataclass
class PriorityQueue:
    heap: List[Tuple[float, int, str]] = field(default_factory=list)
    counter: int = 0

    def push(self, item: str, priority: float) -> None:
        heapq.heappush(self.heap, (priority, self.counter, item))
        self.counter += 1

    def pop(self) -> Optional[str]:
        return heapq.heappop(self.heap)[2] if self.heap else None

    def peek(self) -> Optional[str]:
        return self.heap[0][2] if self.heap else None

    def stats(self) -> dict:
        return {"size": len(self.heap), "top": self.peek()}

def run():
    pq = PriorityQueue()
    pq.push("task1", 3); pq.push("task2", 1); pq.push("task3", 2)
    print("Pop order:", pq.pop(), pq.pop(), pq.pop())
    print("Stats:", pq.stats())

if __name__ == "__main__": run()
