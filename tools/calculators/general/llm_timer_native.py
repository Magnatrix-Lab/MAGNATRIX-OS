"""Timer — countdown, interval, stopwatch, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum, auto
import time

class Timer:
    def __init__(self):
        self.timers: Dict[str, Dict] = {}
        self.history: List[Dict] = []

    def set_timeout(self, timer_id: str, delay: float, callback: Callable):
        self.timers[timer_id] = {"type": "timeout", "expires": time.time() + delay, "callback": callback, "active": True}

    def set_interval(self, timer_id: str, interval: float, callback: Callable):
        self.timers[timer_id] = {"type": "interval", "interval": interval, "next": time.time() + interval, "callback": callback, "active": True}

    def stopwatch_start(self, timer_id: str):
        self.timers[timer_id] = {"type": "stopwatch", "start": time.time(), "active": True}

    def stopwatch_elapsed(self, timer_id: str) -> float:
        t = self.timers.get(timer_id)
        if t and t["type"] == "stopwatch":
            return time.time() - t["start"]
        return 0.0

    def cancel(self, timer_id: str):
        if timer_id in self.timers:
            self.timers[timer_id]["active"] = False

    def tick(self):
        now = time.time()
        for tid, t in list(self.timers.items()):
            if not t.get("active"):
                continue
            if t["type"] == "timeout" and now >= t["expires"]:
                t["callback"]()
                t["active"] = False
                self.history.append({"id": tid, "type": "timeout", "time": now})
            elif t["type"] == "interval" and now >= t["next"]:
                t["callback"]()
                t["next"] = now + t["interval"]
                self.history.append({"id": tid, "type": "interval", "time": now})

    def stats(self) -> Dict:
        active = sum(1 for t in self.timers.values() if t.get("active"))
        return {"timers": len(self.timers), "active": active, "history": len(self.history)}

def run():
    timer = Timer()
    def cb():
        print("Tick!")
    timer.set_timeout("t1", 0.1, cb)
    timer.set_interval("t2", 0.2, cb)
    timer.stopwatch_start("sw")
    for _ in range(5):
        timer.tick()
        time.sleep(0.05)
    print("Elapsed:", timer.stopwatch_elapsed("sw"))
    print(timer.stats())

if __name__ == "__main__":
    run()
