#!/usr/bin/env python3
"""Chaos Engineering for MAGNATRIX-OS — Random failure injection."""
from __future__ import annotations
import random, time
from typing import Any, Callable, Dict, List, Optional

class ChaosEngineering:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self._faults: List[Dict[str, Any]] = []

    def inject_latency(self, fn: Callable, delay: float = 0.5) -> Callable:
        def wrapper(*args, **kwargs):
            if self.enabled and random.random() < 0.1:
                time.sleep(delay)
            return fn(*args, **kwargs)
        return wrapper

    def inject_error(self, fn: Callable, error_rate: float = 0.05) -> Callable:
        def wrapper(*args, **kwargs):
            if self.enabled and random.random() < error_rate:
                raise RuntimeError("Chaos: injected failure")
            return fn(*args, **kwargs)
        return wrapper

    def start(self) -> None:
        self.enabled = True

    def stop(self) -> None:
        self.enabled = False

    def stats(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "faults": len(self._faults)}
