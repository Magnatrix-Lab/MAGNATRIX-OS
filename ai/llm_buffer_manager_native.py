"""
llm_buffer_manager_native.py
MAGNATRIX-OS Buffer Manager Engine
Native Python, stdlib only.
Provides streaming buffer management, windowing, watermark tracking, and backpressure handling.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class BufferWindow:
    items: List[Any]
    start_time: float
    end_time: float
    watermark: float

    def to_dict(self) -> Dict[str, Any]:
        return {"items": len(self.items), "start": self.start_time, "end": self.end_time, "watermark": self.watermark}


class BufferManagerEngine:
    """Streaming buffer with windowing and watermark management."""

    def __init__(self, max_size: int = 1000, watermark_delay: float = 1.0) -> None:
        self.max_size = max_size
        self.watermark_delay = watermark_delay
        self._buffer: List[Tuple[float, Any]] = []  # (timestamp, item)
        self._handlers: List[Callable[[BufferWindow], None]] = []
        self._dropped = 0

    def add(self, item: Any, timestamp: Optional[float] = None) -> bool:
        ts = timestamp if timestamp is not None else time.time()
        if len(self._buffer) >= self.max_size:
            self._buffer.pop(0)
            self._dropped += 1
        self._buffer.append((ts, item))
        return True

    def get_window(self, start_time: float, end_time: float) -> List[Any]:
        return [item for ts, item in self._buffer if start_time <= ts <= end_time]

    def get_watermark(self) -> float:
        if not self._buffer:
            return time.time()
        return max(ts for ts, _ in self._buffer) - self.watermark_delay

    def emit_window(self, start_time: float, end_time: float) -> BufferWindow:
        items = self.get_window(start_time, end_time)
        window = BufferWindow(items, start_time, end_time, self.get_watermark())
        for handler in self._handlers:
            try:
                handler(window)
            except Exception:
                pass
        return window

    def get_latest(self, n: int = 10) -> List[Any]:
        return [item for _, item in self._buffer[-n:]]

    def add_handler(self, handler: Callable[[BufferWindow], None]) -> None:
        self._handlers.append(handler)

    def flush(self) -> BufferWindow:
        if not self._buffer:
            return BufferWindow([], 0, 0, 0)
        start = min(ts for ts, _ in self._buffer)
        end = max(ts for ts, _ in self._buffer)
        return self.emit_window(start, end)

    def clear(self) -> None:
        self._buffer.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._buffer), "max_size": self.max_size,
            "dropped": self._dropped, "watermark": self.get_watermark(),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Buffer Manager Engine")
    print("=" * 60)

    engine = BufferManagerEngine(max_size=50, watermark_delay=0.5)

    def window_handler(window: BufferWindow) -> None:
        print(f"  [Window] {window.items} items, watermark={window.watermark:.2f}")

    engine.add_handler(window_handler)

    print("\n--- Add items ---")
    base = time.time()
    for i in range(20):
        engine.add(f"item_{i}", base + i * 0.1)

    print("\n--- Get window ---")
    items = engine.get_window(base, base + 1.0)
    print(f"  Items in window: {len(items)}")

    print("\n--- Emit window ---")
    engine.emit_window(base, base + 1.0)

    print("\n--- Watermark ---")
    print(f"  Watermark: {engine.get_watermark():.2f}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nBuffer Manager test complete.")


if __name__ == "__main__":
    run()
