"""Timeout Handler — deadline enforcement, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, Dict
from threading import Thread, Event
import time

class TimeoutHandler:
    def __init__(self, default_timeout: float = 5.0):
        self.default_timeout = default_timeout
        self.history: List[Dict] = []

    def execute(self, func: Callable, timeout: Optional[float] = None, *args, **kwargs) -> Any:
        timeout = timeout or self.default_timeout
        result = [None]
        exception = [None]
        completed = Event()

        def wrapper():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
            finally:
                completed.set()

        thread = Thread(target=wrapper)
        thread.start()
        finished = completed.wait(timeout=timeout)
        if not finished:
            self.history.append({"func": func.__name__, "timeout": timeout, "timed_out": True, "time": time.time()})
            raise TimeoutError(f"Function timed out after {timeout} seconds")
        self.history.append({"func": func.__name__, "timeout": timeout, "timed_out": False, "time": time.time()})
        if exception[0]:
            raise exception[0]
        return result[0]

    def stats(self) -> Dict:
        timeouts = sum(1 for h in self.history if h["timed_out"])
        return {"total": len(self.history), "timeouts": timeouts, "default_timeout": self.default_timeout}

def run():
    handler = TimeoutHandler(default_timeout=0.5)
    def slow():
        time.sleep(1)
        return "done"
    def fast():
        time.sleep(0.1)
        return "done"
    try:
        print(handler.execute(fast, timeout=1.0))
    except Exception as e:
        print(e)
    try:
        print(handler.execute(slow, timeout=0.2))
    except Exception as e:
        print(e)
    print(handler.stats())

if __name__ == "__main__":
    run()
