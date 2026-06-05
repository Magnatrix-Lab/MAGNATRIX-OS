"""Bulkhead Pattern — resource isolation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from queue import Queue
from threading import Thread, Lock
import time

class BulkheadPool:
    def __init__(self, pool_id: str, capacity: int, queue_size: int = 10):
        self.pool_id = pool_id
        self.capacity = capacity
        self.queue_size = queue_size
        self.active = 0
        self.queued = 0
        self.lock = Lock()
        self.task_queue = Queue(maxsize=queue_size)
        self.rejected = 0
        self.completed = 0

    def execute(self, func: Callable, *args, **kwargs) -> Optional[Any]:
        with self.lock:
            if self.active >= self.capacity and self.task_queue.full():
                self.rejected += 1
                raise Exception(f"Bulkhead {self.pool_id} full")
            if self.active < self.capacity:
                self.active += 1
                try:
                    result = func(*args, **kwargs)
                    self.completed += 1
                    return result
                finally:
                    with self.lock:
                        self.active -= 1
            else:
                self.task_queue.put((func, args, kwargs))
                self.queued += 1
                return None

    def stats(self) -> Dict:
        return {"pool_id": self.pool_id, "capacity": self.capacity, "active": self.active, "queued": self.queued, "rejected": self.rejected, "completed": self.completed}

class BulkheadManager:
    def __init__(self):
        self.pools: Dict[str, BulkheadPool] = {}

    def create_pool(self, pool_id: str, capacity: int, queue_size: int = 10):
        self.pools[pool_id] = BulkheadPool(pool_id, capacity, queue_size)

    def execute(self, pool_id: str, func: Callable, *args, **kwargs) -> Any:
        pool = self.pools.get(pool_id)
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        return pool.execute(func, *args, **kwargs)

    def stats(self) -> Dict:
        return {"pools": len(self.pools), "details": {k: v.stats() for k, v in self.pools.items()}}

def run():
    manager = BulkheadManager()
    manager.create_pool("db", capacity=2)
    def query():
        time.sleep(0.1)
        return "result"
    for i in range(5):
        try:
            r = manager.execute("db", query)
            print(f"Call {i}: {r}")
        except Exception as e:
            print(f"Call {i}: {e}")
    print(manager.stats())

if __name__ == "__main__":
    run()
