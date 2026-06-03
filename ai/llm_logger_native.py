"""LLM Logger — Native Python (stdlib only)."""
from __future__ import annotations
import sys, json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime

class LogLevel(Enum):
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    FATAL = auto()

@dataclass
class LogEntry:
    id: str
    timestamp: str
    level: LogLevel
    source: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class Logger:
    def __init__(self, min_level: LogLevel = LogLevel.INFO, max_entries: int = 10000) -> None:
        self.min_level = min_level
        self.max_entries = max_entries
        self._entries: List[LogEntry] = []
        self._handlers: List[Dict[str, Any]] = []

    def add_handler(self, handler, level: LogLevel = LogLevel.DEBUG) -> None:
        self._handlers.append({"handler": handler, "level": level})

    def _should_log(self, level: LogLevel) -> bool:
        return level.value >= self.min_level.value

    def log(self, level: LogLevel, source: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        if not self._should_log(level):
            return
        entry = LogEntry(
            id="log_" + str(len(self._entries)),
            timestamp=datetime.now().isoformat(),
            level=level,
            source=source,
            message=message,
            metadata=metadata or {}
        )
        if len(self._entries) >= self.max_entries:
            self._entries.pop(0)
        self._entries.append(entry)
        for h in self._handlers:
            if level.value >= h["level"].value:
                h["handler"](entry)

    def debug(self, source: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.log(LogLevel.DEBUG, source, message, metadata)

    def info(self, source: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.log(LogLevel.INFO, source, message, metadata)

    def warning(self, source: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.log(LogLevel.WARNING, source, message, metadata)

    def error(self, source: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.log(LogLevel.ERROR, source, message, metadata)

    def fatal(self, source: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.log(LogLevel.FATAL, source, message, metadata)

    def query(self, level: Optional[LogLevel] = None, source: Optional[str] = None, limit: int = 100) -> List[LogEntry]:
        results = self._entries
        if level:
            results = [e for e in results if e.level == level]
        if source:
            results = [e for e in results if e.source == source]
        return results[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for e in self._entries:
            counts[e.level.name] = counts.get(e.level.name, 0) + 1
        return {"total": len(self._entries), "by_level": counts}

def run() -> None:
    print("Logger test")
    e = Logger(min_level=LogLevel.DEBUG)
    e.add_handler(lambda entry: print("  [HANDLER] " + entry.level.name + ": " + entry.message), LogLevel.INFO)
    e.debug("test", "Debug message")
    e.info("test", "Info message")
    e.warning("test", "Warning message")
    e.error("test", "Error message")
    print("  Total entries: " + str(len(e.query())))
    print("  Errors: " + str(len(e.query(level=LogLevel.ERROR))))
    print("  Stats: " + str(e.get_stats()))
    print("Logger test complete.")

if __name__ == "__main__":
    run()
