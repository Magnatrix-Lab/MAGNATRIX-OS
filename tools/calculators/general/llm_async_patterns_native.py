"""Async Patterns & Futures — native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional
from concurrent.futures import Future, ThreadPoolExecutor
import time

@dataclass
class AsyncTask:
    task_id: str
    future: Future
    status: str = "running"

class AsyncPatternEngine:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, AsyncTask] = {}

    def submit(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        future = self.executor.submit(func, *args, **kwargs)
        self.tasks[task_id] = AsyncTask(task_id, future)
        return task_id

    def result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        task = self.tasks[task_id]
        try:
            val = task.future.result(timeout=timeout)
            task.status = "done"
            return val
        except Exception as e:
            task.status = "error"
            raise e

    def done(self, task_id: str) -> bool:
        return self.tasks[task_id].future.done()

    def wait_all(self, task_ids: List[str], timeout: Optional[float] = None):
        for tid in task_ids:
            self.result(tid, timeout=timeout)

    def as_completed(self, task_ids: List[str]):
        pending = set(task_ids)
        while pending:
            for tid in list(pending):
                if self.done(tid):
                    yield tid, self.result(tid)
                    pending.remove(tid)
            time.sleep(0.01)

    def stats(self) -> Dict:
        statuses = {}
        for t in self.tasks.values():
            s = "done" if t.future.done() else "running"
            statuses[s] = statuses.get(s, 0) + 1
        return {"tasks": len(self.tasks), "statuses": statuses}

    def shutdown(self):
        self.executor.shutdown(wait=True)

def run():
    engine = AsyncPatternEngine(max_workers=3)
    for i in range(5):
        engine.submit(f"task_{i}", lambda x: time.sleep(0.1) or x*2, i)
    print(engine.stats())
    for tid, val in engine.as_completed([f"task_{i}" for i in range(5)]):
        print(f"{tid} = {val}")
    engine.shutdown()

if __name__ == "__main__":
    run()
