"""
llm_rolling_window_native.py
MAGNATRIX-OS Rolling Window Analytics Engine
Native Python, stdlib only.
Provides tumbling, sliding, and session windows with aggregations, triggers, and watermark support.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class WindowType(Enum):
    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"


@dataclass
class WindowEvent:
    timestamp: float
    key: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"timestamp": self.timestamp, "key": self.key, "value": self.value, "metadata": self.metadata}


@dataclass
class WindowResult:
    window_start: float
    window_end: float
    key: str
    count: int
    aggregates: Dict[str, Any]
    events: List[WindowEvent]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_start": self.window_start, "window_end": self.window_end,
            "key": self.key, "count": self.count, "aggregates": self.aggregates,
            "events": [e.to_dict() for e in self.events],
        }


class RollingWindowEngine:
    """
    Rolling window analytics with tumbling, sliding, and session windows.
    """

    def __init__(self, watermark_delay: float = 0.0) -> None:
        self.watermark_delay = watermark_delay
        self._events: List[WindowEvent] = []
        self._handlers: List[Callable[[WindowResult], None]] = []

    def add_event(self, event: WindowEvent) -> None:
        self._events.append(event)

    def _emit(self, result: WindowResult) -> None:
        for handler in self._handlers:
            try:
                handler(result)
            except Exception:
                pass

    def add_handler(self, handler: Callable[[WindowResult], None]) -> None:
        self._handlers.append(handler)

    def tumbling(self, key: str, window_size_seconds: float, start_time: Optional[float] = None) -> List[WindowResult]:
        events = [e for e in self._events if e.key == key]
        if not events:
            return []
        if start_time is None:
            start_time = min(e.timestamp for e in events)
        end_time = max(e.timestamp for e in events)

        results = []
        current_start = start_time
        while current_start <= end_time:
            current_end = current_start + window_size_seconds
            window_events = [e for e in events if current_start <= e.timestamp < current_end]
            if window_events:
                results.append(self._aggregate(current_start, current_end, key, window_events))
            current_start = current_end
        return results

    def sliding(self, key: str, window_size_seconds: float, slide_seconds: float,
                start_time: Optional[float] = None) -> List[WindowResult]:
        events = [e for e in self._events if e.key == key]
        if not events:
            return []
        if start_time is None:
            start_time = min(e.timestamp for e in events)
        end_time = max(e.timestamp for e in events)

        results = []
        current_start = start_time
        while current_start <= end_time:
            current_end = current_start + window_size_seconds
            window_events = [e for e in events if current_start <= e.timestamp < current_end]
            if window_events:
                results.append(self._aggregate(current_start, current_end, key, window_events))
            current_start += slide_seconds
        return results

    def session(self, key: str, gap_seconds: float) -> List[WindowResult]:
        events = sorted([e for e in self._events if e.key == key], key=lambda e: e.timestamp)
        if not events:
            return []

        results = []
        session_start = events[0].timestamp
        session_events = [events[0]]

        for i in range(1, len(events)):
            if events[i].timestamp - events[i - 1].timestamp > gap_seconds:
                results.append(self._aggregate(session_start, events[i - 1].timestamp + 0.001, key, session_events))
                session_start = events[i].timestamp
                session_events = []
            session_events.append(events[i])

        if session_events:
            results.append(self._aggregate(session_start, events[-1].timestamp + 0.001, key, session_events))
        return results

    def _aggregate(self, start: float, end: float, key: str, events: List[WindowEvent]) -> WindowResult:
        values = [e.value for e in events if isinstance(e.value, (int, float))]
        aggregates: Dict[str, Any] = {
            "count": len(events),
            "sum": sum(values) if values else 0,
            "avg": sum(values) / len(values) if values else 0,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
        return WindowResult(window_start=start, window_end=end, key=key, count=len(events), aggregates=aggregates, events=events)

    def clear(self) -> None:
        self._events.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {"total_events": len(self._events), "keys": len(set(e.key for e in self._events))}


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Rolling Window Analytics Engine")
    print("=" * 60)

    engine = RollingWindowEngine()

    base = time.time()
    events = [
        WindowEvent(base + 1, "api_latency", 120), WindowEvent(base + 2, "api_latency", 150),
        WindowEvent(base + 3, "api_latency", 110), WindowEvent(base + 5, "api_latency", 200),
        WindowEvent(base + 6, "api_latency", 130), WindowEvent(base + 8, "api_latency", 90),
        WindowEvent(base + 12, "api_latency", 300), WindowEvent(base + 13, "api_latency", 250),
        WindowEvent(base + 20, "api_latency", 100),
    ]
    for e in events:
        engine.add_event(e)

    print("\n--- Tumbling windows (5s) ---")
    results = engine.tumbling("api_latency", 5.0, start_time=base)
    for r in results:
        print(f"  [{r.window_start - base:.0f}-{r.window_end - base:.0f}s] count={r.count} avg={r.aggregates['avg']:.0f}")

    print("\n--- Sliding windows (5s, 2s slide) ---")
    results = engine.sliding("api_latency", 5.0, 2.0, start_time=base)
    for r in results[:4]:
        print(f"  [{r.window_start - base:.0f}-{r.window_end - base:.0f}s] count={r.count} avg={r.aggregates['avg']:.0f}")

    print("\n--- Session windows (3s gap) ---")
    results = engine.session("api_latency", 3.0)
    for r in results:
        print(f"  [{r.window_start - base:.0f}-{r.window_end - base:.0f}s] count={r.count} avg={r.aggregates['avg']:.0f}")

    print("\nRolling Window test complete.")


if __name__ == "__main__":
    run()
