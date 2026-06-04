"""Log Aggregator — structured logging, filtering, aggregation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum, auto
import time
import re

class LogLevel(Enum):
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 4
    FATAL = 5

@dataclass
class LogEntry:
    timestamp: float
    level: LogLevel
    source: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)

class LogAggregator:
    def __init__(self, min_level: LogLevel = LogLevel.DEBUG):
        self.min_level = min_level
        self.entries: List[LogEntry] = []
        self.filters: List[Callable[[LogEntry], bool]] = []

    def log(self, level: LogLevel, source: str, message: str, context: Dict = None):
        if level.value < self.min_level.value:
            return
        entry = LogEntry(time.time(), level, source, message, context or {})
        self.entries.append(entry)

    def debug(self, source: str, message: str, context: Dict = None):
        self.log(LogLevel.DEBUG, source, message, context)

    def info(self, source: str, message: str, context: Dict = None):
        self.log(LogLevel.INFO, source, message, context)

    def error(self, source: str, message: str, context: Dict = None):
        self.log(LogLevel.ERROR, source, message, context)

    def add_filter(self, filter_fn: Callable[[LogEntry], bool]):
        self.filters.append(filter_fn)

    def query(self, level: Optional[LogLevel] = None, source: Optional[str] = None, pattern: Optional[str] = None) -> List[LogEntry]:
        results = self.entries
        if level:
            results = [e for e in results if e.level == level]
        if source:
            results = [e for e in results if e.source == source]
        if pattern:
            results = [e for e in results if re.search(pattern, e.message)]
        for f in self.filters:
            results = [e for e in results if f(e)]
        return results

    def aggregate_by_level(self) -> Dict[str, int]:
        counts = {}
        for e in self.entries:
            counts[e.level.name] = counts.get(e.level.name, 0) + 1
        return counts

    def aggregate_by_source(self) -> Dict[str, int]:
        counts = {}
        for e in self.entries:
            counts[e.source] = counts.get(e.source, 0) + 1
        return counts

    def stats(self) -> Dict:
        return {"total": len(self.entries), "by_level": self.aggregate_by_level(), "by_source": self.aggregate_by_source()}

def run():
    agg = LogAggregator(min_level=LogLevel.INFO)
    agg.info("api", "Request received", {"path": "/users"})
    agg.info("db", "Query executed", {"sql": "SELECT *"})
    agg.error("api", "Connection failed", {"error": "timeout"})
    agg.debug("api", "Debug info", {})
    print(agg.query(level=LogLevel.INFO))
    print(agg.stats())

if __name__ == "__main__":
    run()
