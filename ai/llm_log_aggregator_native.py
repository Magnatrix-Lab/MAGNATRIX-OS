"""
llm_log_aggregator_native.py
MAGNATRIX-OS Log Aggregator Engine
Native Python, stdlib only.
Provides log aggregation, filtering, pattern detection, structured parsing, and export.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    timestamp: float
    level: LogLevel
    source: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp, "level": self.level.value,
            "source": self.source, "message": self.message[:100],
            "metadata": self.metadata,
        }


class LogAggregatorEngine:
    """Log aggregation with filtering and pattern detection."""

    def __init__(self, max_entries: int = 10000) -> None:
        self.max_entries = max_entries
        self._entries: List[LogEntry] = []
        self._patterns: Dict[str, int] = {}
        self._handlers: List[Callable[[LogEntry], None]] = []

    def log(self, level: LogLevel, source: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> LogEntry:
        entry = LogEntry(timestamp=time.time(), level=level, source=source, message=message, metadata=metadata or {})
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries.pop(0)
        self._update_patterns(message)
        for handler in self._handlers:
            try:
                handler(entry)
            except Exception:
                pass
        return entry

    def _update_patterns(self, message: str) -> None:
        # Extract error patterns
        patterns = re.findall(r'[A-Z][a-zA-Z]+Error|Exception|Failed|Timeout|Refused', message)
        for p in patterns:
            self._patterns[p] = self._patterns.get(p, 0) + 1

    def add_handler(self, handler: Callable[[LogEntry], None]) -> None:
        self._handlers.append(handler)

    def query(self, level: Optional[LogLevel] = None, source: Optional[str] = None,
              start_time: Optional[float] = None, end_time: Optional[float] = None,
              pattern: Optional[str] = None, limit: int = 100) -> List[LogEntry]:
        results = self._entries
        if level:
            results = [e for e in results if e.level == level]
        if source:
            results = [e for e in results if e.source == source]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        if pattern:
            results = [e for e in results if pattern in e.message]
        return results[-limit:]

    def get_error_rate(self, window_seconds: float = 3600) -> float:
        now = time.time()
        recent = [e for e in self._entries if e.timestamp >= now - window_seconds]
        errors = [e for e in recent if e.level in (LogLevel.ERROR, LogLevel.CRITICAL)]
        return len(errors) / len(recent) if recent else 0.0

    def get_patterns(self, min_count: int = 2) -> Dict[str, int]:
        return {k: v for k, v in self._patterns.items() if v >= min_count}

    def get_stats(self) -> Dict[str, Any]:
        by_level: Dict[str, int] = {}
        for e in self._entries:
            by_level[e.level.value] = by_level.get(e.level.value, 0) + 1
        return {
            "total_entries": len(self._entries), "by_level": by_level,
            "error_rate": self.get_error_rate(), "patterns": len(self._patterns),
        }

    def export(self, path: str, level: Optional[LogLevel] = None) -> None:
        entries = self.query(level=level)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in entries], f, indent=2, default=str)

    def clear(self) -> None:
        self._entries.clear()
        self._patterns.clear()


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Log Aggregator Engine")
    print("=" * 60)

    engine = LogAggregatorEngine(max_entries=1000)

    def error_handler(entry: LogEntry) -> None:
        if entry.level in (LogLevel.ERROR, LogLevel.CRITICAL):
            print(f"  [ALERT] {entry.source}: {entry.message[:60]}")

    engine.add_handler(error_handler)

    print("\n--- Log entries ---")
    engine.log(LogLevel.INFO, "api", "Request received")
    engine.log(LogLevel.INFO, "api", "Processing complete")
    engine.log(LogLevel.WARNING, "db", "Slow query detected")
    engine.log(LogLevel.ERROR, "api", "ConnectionTimeoutError: failed to connect")
    engine.log(LogLevel.ERROR, "api", "ConnectionTimeoutError: retry failed")
    engine.log(LogLevel.CRITICAL, "system", "OutOfMemoryError: heap exhausted")

    print("\n--- Query errors ---")
    errors = engine.query(level=LogLevel.ERROR)
    for e in errors:
        print(f"  {e.source}: {e.message}")

    print("\n--- Patterns ---")
    patterns = engine.get_patterns()
    for p, count in patterns.items():
        print(f"  {p}: {count}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nLog Aggregator test complete.")


if __name__ == "__main__":
    run()
