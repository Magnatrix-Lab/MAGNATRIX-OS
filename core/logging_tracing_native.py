#!/usr/bin/env python3
"""
Logging & Tracing for MAGNATRIX-OS
Structured logging with correlation IDs, log rotation, request tracing
across modules, and severity-based filtering.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


class LogLevel(enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"

    def __int__(self) -> int:
        return {LogLevel.DEBUG: 10, LogLevel.INFO: 20, LogLevel.WARN: 30, LogLevel.ERROR: 40, LogLevel.FATAL: 50}[self]


@dataclasses.dataclass
class LogEntry:
    timestamp: float
    level: LogLevel
    message: str
    correlation_id: str
    module: str
    function: str
    line: int
    thread_id: int
    context: Dict[str, Any] = dataclasses.field(default_factory=dict)
    exception: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self.timestamp)) + f".{int((self.timestamp % 1) * 1000):03d}Z",
            "level": self.level.value,
            "msg": self.message,
            "corr_id": self.correlation_id,
            "module": self.module,
            "func": self.function,
            "line": self.line,
            "thread": self.thread_id,
            "context": self.context,
            "exc": self.exception,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span": self.parent_span_id,
            "dur_ms": self.duration_ms,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class TracingSpan:
    """Represents a single trace span."""

    def __init__(self, trace_id: str, span_id: str, name: str, parent_span_id: Optional[str] = None) -> None:
        self.trace_id = trace_id
        self.span_id = span_id
        self.name = name
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.annotations: List[Dict[str, Any]] = []

    def end(self) -> None:
        self.end_time = time.time()

    def add_annotation(self, message: str) -> None:
        self.annotations.append({"timestamp": time.time(), "message": message})

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "name": self.name,
            "parent_span": self.parent_span_id,
            "start": self.start_time,
            "end": self.end_time,
            "duration_ms": self.duration_ms,
            "annotations": self.annotations,
        }


class LoggingManager:
    """Centralized structured logging with tracing and rotation."""

    def __init__(self, log_dir: str = "/tmp/magnatrix_logs", min_level: LogLevel = LogLevel.INFO, max_file_size: int = 10 * 1024 * 1024, max_files: int = 5) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.min_level = min_level
        self.max_file_size = max_file_size
        self.max_files = max_files
        self._current_log = self.log_dir / "magnatrix.log"
        self._lock = threading.Lock()
        self._hooks: List[Callable[[LogEntry], None]] = []
        self._trace_context = threading.local()

    # ------------------------------------------------------------------
    # Correlation & tracing
    # ------------------------------------------------------------------

    def set_correlation_id(self, corr_id: str) -> None:
        self._trace_context.corr_id = corr_id
        self._trace_context.trace_id = corr_id
        self._trace_context.span_stack = []

    def get_correlation_id(self) -> str:
        return getattr(self._trace_context, "corr_id", "none")

    def start_span(self, name: str) -> TracingSpan:
        trace_id = getattr(self._trace_context, "trace_id", "none")
        parent_span_id = None
        span_stack = getattr(self._trace_context, "span_stack", [])
        if span_stack:
            parent_span_id = span_stack[-1].span_id
        span = TracingSpan(trace_id, self._gen_id(), name, parent_span_id)
        span_stack.append(span)
        self._trace_context.span_stack = span_stack
        return span

    def end_span(self, span: TracingSpan) -> None:
        span.end()
        span_stack = getattr(self._trace_context, "span_stack", [])
        if span in span_stack:
            span_stack.remove(span)
        self._trace_context.span_stack = span_stack

    def _gen_id(self) -> str:
        return f"{time.time():.6f}-{threading.current_thread().ident}"

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _should_log(self, level: LogLevel) -> bool:
        return int(level) >= int(self.min_level)

    def _write(self, entry: LogEntry) -> None:
        with self._lock:
            self._rotate_if_needed()
            with open(self._current_log, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        for hook in self._hooks:
            try:
                hook(entry)
            except Exception:
                pass

    def _rotate_if_needed(self) -> None:
        if self._current_log.exists() and self._current_log.stat().st_size > self.max_file_size:
            # Rotate: move current to .1, .2, etc.
            for i in range(self.max_files - 1, 0, -1):
                old = self.log_dir / f"magnatrix.log.{i}"
                new = self.log_dir / f"magnatrix.log.{i + 1}"
                if old.exists():
                    old.rename(new)
            self._current_log.rename(self.log_dir / "magnatrix.log.1")

    def _log(self, level: LogLevel, message: str, context: Optional[Dict[str, Any]] = None, exc: Optional[Exception] = None) -> None:
        if not self._should_log(level):
            return
        frame = traceback.extract_stack(limit=3)[0]
        span_stack = getattr(self._trace_context, "span_stack", [])
        current_span = span_stack[-1] if span_stack else None
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            message=message,
            correlation_id=self.get_correlation_id(),
            module=Path(frame.filename).stem,
            function=frame.name,
            line=frame.lineno,
            thread_id=threading.current_thread().ident or 0,
            context=context or {},
            exception=traceback.format_exc() if exc else None,
            trace_id=current_span.trace_id if current_span else None,
            span_id=current_span.span_id if current_span else None,
            parent_span_id=current_span.parent_span_id if current_span else None,
        )
        self._write(entry)

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self._log(LogLevel.DEBUG, message, context)

    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self._log(LogLevel.INFO, message, context)

    def warn(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self._log(LogLevel.WARN, message, context)

    def error(self, message: str, context: Optional[Dict[str, Any]] = None, exc: Optional[Exception] = None) -> None:
        self._log(LogLevel.ERROR, message, context, exc)

    def fatal(self, message: str, context: Optional[Dict[str, Any]] = None, exc: Optional[Exception] = None) -> None:
        self._log(LogLevel.FATAL, message, context, exc)

    # ------------------------------------------------------------------
    # Hooks & filtering
    # ------------------------------------------------------------------

    def add_hook(self, hook: Callable[[LogEntry], None]) -> None:
        self._hooks.append(hook)

    def remove_hook(self, hook: Callable[[LogEntry], None]) -> None:
        if hook in self._hooks:
            self._hooks.remove(hook)

    def get_entries(self, level: Optional[LogLevel] = None, corr_id: Optional[str] = None, limit: int = 100) -> List[LogEntry]:
        entries = []
        if not self._current_log.exists():
            return []
        with open(self._current_log, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if level and data.get("level") != level.value:
                        continue
                    if corr_id and data.get("corr_id") != corr_id:
                        continue
                    entries.append(data)
                except Exception:
                    pass
        return entries[-limit:]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        total_bytes = 0
        file_count = 0
        for f in self.log_dir.glob("magnatrix.log*"):
            total_bytes += f.stat().st_size
            file_count += 1
        return {
            "log_dir": str(self.log_dir),
            "min_level": self.min_level.value,
            "total_bytes": total_bytes,
            "file_count": file_count,
            "hooks": len(self._hooks),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="magnatrix_logs_")
    logger = LoggingManager(log_dir=tmp, min_level=LogLevel.DEBUG, max_file_size=1024 * 1024)
    print("=== Logging & Tracing Demo ===\n")
    # Set correlation
    logger.set_correlation_id("req-abc-123")
    # Start a trace span
    span = logger.start_span("process_request")
    logger.info("Processing started", {"user_id": "u1", "action": "calculate"})
    logger.debug("Internal state", {"step": 1, "value": 42})
    # Simulate error
    try:
        1 / 0
    except Exception as e:
        logger.error("Calculation failed", {"input": 1}, exc=e)
    logger.end_span(span)
    # Stats
    print(f"Stats: {logger.stats()}")
    # Read back entries
    entries = logger.get_entries()
    print(f"\nLogged entries: {len(entries)}")
    for e in entries[:3]:
        print(f"  [{e['level']}] {e['msg']} (corr={e['corr_id']}, trace={e.get('trace_id')})")
    # Cleanup
    import shutil
    shutil.rmtree(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
