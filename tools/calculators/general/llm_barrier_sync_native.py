"""Barrier Synchronization & Rendezvous — native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional
from threading import Thread, Lock, Event
import time

class Barrier:
    def __init__(self, count: int):
        self.count = count
        self.current = 0
        self.lock = Lock()
        self.event = Event()

    def wait(self):
        with self.lock:
            self.current += 1
            if self.current >= self.count:
                self.event.set()
        self.event.wait()
        return True

    def reset(self):
        with self.lock:
            self.current = 0
            self.event.clear()

    def stats(self) -> Dict:
        return {"count": self.count, "current": self.current, "triggered": self.event.is_set()}

class Rendezvous:
    def __init__(self, parties: List[str]):
        self.parties = parties
        self.arrived: Dict[str, bool] = {p: False for p in parties}
        self.lock = Lock()
        self.event = Event()

    def arrive(self, party: str) -> bool:
        with self.lock:
            self.arrived[party] = True
            if all(self.arrived.values()):
                self.event.set()
        self.event.wait(timeout=5)
        return self.event.is_set()

    def reset(self):
        with self.lock:
            for p in self.arrived:
                self.arrived[p] = False
            self.event.clear()

    def stats(self) -> Dict:
        return {"parties": self.parties, "arrived": {k: v for k, v in self.arrived.items()}, "complete": self.event.is_set()}

def run():
    barrier = Barrier(count=3)
    results = []
    def worker(i):
        time.sleep(0.1 * i)
        barrier.wait()
        results.append(i)
    threads = [Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads: t.start()
    for t in threads: t.join()
    print("Barrier results:", results, barrier.stats())

    rv = Rendezvous(["A", "B"])
    def a(): time.sleep(0.1); rv.arrive("A")
    def b(): time.sleep(0.2); rv.arrive("B")
    t1 = Thread(target=a); t2 = Thread(target=b)
    t1.start(); t2.start()
    t1.join(); t2.join()
    print("Rendezvous:", rv.stats())

if __name__ == "__main__":
    run()
