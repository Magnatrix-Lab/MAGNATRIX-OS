"""Thread Pool Executor — native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional
from queue import Queue
from threading import Thread, Lock
import time
import uuid

@dataclass
class Task:
    task_id: str
    func: Callable
    args: tuple
    kwargs: Dict
    result: Any = None
    status: str = "pending"
    error: Optional[str] = None

class ThreadPool:
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self.task_queue: Queue = Queue()
        self.results: Dict[str, Task] = {}
        self.lock = Lock()
        self.workers: List[Thread] = []
        self.running = False

    def _worker(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                try:
                    task.result = task.func(*task.args, **task.kwargs)
                    task.status = "done"
                except Exception as e:
                    task.error = str(e)
                    task.status = "error"
                with self.lock:
                    self.results[task.task_id] = task
                self.task_queue.task_done()
            except:
                pass

    def start(self):
        self.running = True
        for _ in range(self.num_workers):
            t = Thread(target=self._worker)
            t.daemon = True
            t.start()
            self.workers.append(t)

    def submit(self, func: Callable, *args, **kwargs) -> str:
        task_id = str(uuid.uuid4())[:8]
        task = Task(task_id, func, args, kwargs)
        with self.lock:
            self.results[task_id] = task
        self.task_queue.put(task)
        return task_id

    def get_result(self, task_id: str) -> Optional[Task]:
        with self.lock:
            return self.results.get(task_id)

    def shutdown(self):
        self.running = False
        for w in self.workers:
            w.join(timeout=2)

    def stats(self) -> Dict:
        with self.lock:
            statuses = {}
            for t in self.results.values():
                statuses[t.status] = statuses.get(t.status, 0) + 1
            return {"workers": self.num_workers, "tasks": len(self.results), "statuses": statuses, "queue_size": self.task_queue.qsize()}

def run():
    pool = ThreadPool(num_workers=3)
    pool.start()
    ids = [pool.submit(lambda x: x*x, i) for i in range(8)]
    time.sleep(2)
    for tid in ids:
        t = pool.get_result(tid)
        print(f"{tid}: {t.status} = {t.result}")
    print(pool.stats())
    pool.shutdown()

if __name__ == "__main__":
    run()
