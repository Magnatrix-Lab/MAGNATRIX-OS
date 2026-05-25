#!/usr/bin/env python3
"""
kernel/backpressure_native.py
=============================
Backpressure & Flow Control

Prevents memory exhaustion from fast producers + slow consumers.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class BackpressureConfig:
    max_queue_size: int = 10000
    drop_oldest: bool = False  # If True, drop oldest when full; else block
    alert_threshold: float = 0.8  # Alert when queue > 80% full


class BackpressureQueue:
    """Thread-safe queue with backpressure and overflow handling."""

    def __init__(self, config: Optional[BackpressureConfig] = None) -> None:
        self.config = config or BackpressureConfig()
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=self.config.max_queue_size)
        self._dropped = 0
        self._lock = threading.Lock()

    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> bool:
        """Put item into queue. Returns False if dropped or timed out."""
        try:
            self._queue.put(item, block=block, timeout=timeout)
            return True
        except queue.Full:
            if self.config.drop_oldest:
                try:
                    self._queue.get_nowait()
                    self._queue.put_nowait(item)
                    with self._lock:
                        self._dropped += 1
                    return True
                except (queue.Empty, queue.Full):
                    with self._lock:
                        self._dropped += 1
                    return False
            return False

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        return self._queue.get(block=block, timeout=timeout)

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def capacity(self) -> int:
        return self.config.max_queue_size

    @property
    def utilization(self) -> float:
        return self.size / self.capacity if self.capacity > 0 else 0.0

    @property
    def is_alert(self) -> bool:
        return self.utilization > self.config.alert_threshold

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "size": self.size,
                "capacity": self.capacity,
                "utilization": self.utilization,
                "dropped": self._dropped,
                "alert": self.is_alert,
            }
