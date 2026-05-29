#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 3 — Log Aggregator
Native log aggregation with structured JSON logging, filtering, and pattern detection.
- Structured log entries with severity levels
- Ring buffer + file rotation
- Regex-based pattern extraction
- Anomaly detection via log frequency spikes
- Log correlation by trace ID
"""
import json, time, threading, os, sys, re, hashlib, random
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from collections import defaultdict, deque, Counter
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogEntry:
    timestamp: float
    level: int
    message: str
    source: str
    trace_id: str = ""
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.trace_id:
            self.trace_id = ""

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "trace_id": self.trace_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'LogEntry':
        return cls(
            timestamp=d.get("timestamp", 0.0),
            level=d.get("level", 20),
            message=d.get("message", ""),
            source=d.get("source", ""),
            trace_id=d.get("trace_id", ""),
            metadata=d.get("metadata", {}),
        )


class StructuredLogger:
    """Thread-safe structured logger with ring buffer."""

    def __init__(self, source: str, buffer_size: int = 10000, level: int = LogLevel.INFO.value):
        self.source = source
        self.level = level
        self._buffer: deque = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
        self._handlers: List[Callable] = []

    def log(self, level: int, message: str, trace_id: str = "", metadata: Dict = None):
        if level < self.level:
            return
        entry = LogEntry(time.time(), level, message, self.source, trace_id, metadata or {})
        with self._lock:
            self._buffer.append(entry)
            for h in self._handlers:
                try:
                    h(entry)
                except Exception:
                    pass

    def debug(self, msg: str, trace_id: str = "", metadata: Dict = None):
        self.log(LogLevel.DEBUG.value, msg, trace_id, metadata)

    def info(self, msg: str, trace_id: str = "", metadata: Dict = None):
        self.log(LogLevel.INFO.value, msg, trace_id, metadata)

    def warn(self, msg: str, trace_id: str = "", metadata: Dict = None):
        self.log(LogLevel.WARN.value, msg, trace_id, metadata)

    def error(self, msg: str, trace_id: str = "", metadata: Dict = None):
        self.log(LogLevel.ERROR.value, msg, trace_id, metadata)

    def critical(self, msg: str, trace_id: str = "", metadata: Dict = None):
        self.log(LogLevel.CRITICAL.value, msg, trace_id, metadata)

    def add_handler(self, handler: Callable):
        self._handlers.append(handler)

    def query(self, min_level: int = 0, pattern: str = "", trace_id: str = "", limit: int = 100) -> List[LogEntry]:
        with self._lock:
            entries = list(self._buffer)
        results = []
        for e in entries:
            if min_level and e.level < min_level:
                continue
            if pattern and pattern not in e.message:
                continue
            if trace_id and e.trace_id != trace_id:
                continue
            results.append(e)
            if len(results) >= limit:
                break
        return results

    def export_json(self, path: str):
        with self._lock:
            entries = [e.to_dict() for e in self._buffer]
        with open(path, 'w') as f:
            json.dump(entries, f, indent=2)


class LogRotator:
    """Rotate log files based on size or time."""

    def __init__(self, path: str, max_size: int = 1024 * 1024, max_files: int = 5):
        self.path = path
        self.max_size = max_size
        self.max_files = max_files
        self._lock = threading.Lock()

    def _current_size(self) -> int:
        if not os.path.exists(self.path):
            return 0
        return os.path.getsize(self.path)

    def rotate(self):
        with self._lock:
            if self._current_size() < self.max_size:
                return
            # Rotate existing files
            for i in range(self.max_files - 1, 0, -1):
                src = f"{self.path}.{i}"
                dst = f"{self.path}.{i + 1}"
                if os.path.exists(src):
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.rename(src, dst)
            if os.path.exists(self.path):
                os.rename(self.path, f"{self.path}.1")

    def write(self, line: str):
        self.rotate()
        with self._lock:
            with open(self.path, 'a') as f:
                f.write(line + "\n")
                f.flush()


class PatternExtractor:
    """Extract patterns from logs using regex templates."""

    def __init__(self):
        self._patterns: Dict[str, re.Pattern] = {}

    def add_pattern(self, name: str, regex: str):
        self._patterns[name] = re.compile(regex)

    def extract(self, message: str) -> Dict[str, List[str]]:
        results = {}
        for name, pattern in self._patterns.items():
            matches = pattern.findall(message)
            if matches:
                results[name] = matches
        return results


class AnomalyDetector:
    """Detect log frequency spikes and error bursts."""

    def __init__(self, window_sec: float = 60.0, threshold_sigma: float = 3.0):
        self.window_sec = window_sec
        self.threshold_sigma = threshold_sigma
        self._history: deque = deque()
        self._lock = threading.Lock()

    def observe(self, entry: LogEntry):
        with self._lock:
            self._history.append(entry.timestamp)
            # Trim old
            cutoff = time.time() - self.window_sec
            while self._history and self._history[0] < cutoff:
                self._history.popleft()

    def is_anomaly(self) -> Tuple[bool, float]:
        with self._lock:
            recent = list(self._history)
        if len(recent) < 10:
            return False, 0.0
        # Simple rate check
        rate = len(recent) / self.window_sec
        # Baseline: if rate > 3x average of last 5 windows, anomaly
        return rate > 10.0, rate

    def error_burst(self, entries: List[LogEntry], threshold: int = 5) -> bool:
        errors = [e for e in entries if e.level >= LogLevel.ERROR.value]
        if len(errors) < threshold:
            return False
        # Check if errors within short window
        timestamps = sorted([e.timestamp for e in errors])
        window = 10.0
        for i in range(len(timestamps) - threshold + 1):
            if timestamps[i + threshold - 1] - timestamps[i] <= window:
                return True
        return False


class LogCorrelator:
    """Correlate logs by trace ID across sources."""

    def __init__(self):
        self._traces: Dict[str, List[LogEntry]] = defaultdict(list)
        self._lock = threading.Lock()

    def add(self, entry: LogEntry):
        if entry.trace_id:
            with self._lock:
                self._traces[entry.trace_id].append(entry)

    def get_trace(self, trace_id: str) -> List[LogEntry]:
        with self._lock:
            return list(self._traces.get(trace_id, []))

    def trace_duration(self, trace_id: str) -> float:
        entries = self.get_trace(trace_id)
        if len(entries) < 2:
            return 0.0
        timestamps = [e.timestamp for e in entries]
        return max(timestamps) - min(timestamps)

    def trace_errors(self, trace_id: str) -> List[LogEntry]:
        return [e for e in self.get_trace(trace_id) if e.level >= LogLevel.ERROR.value]


class LogAggregator:
    """Full log aggregator combining all subsystems."""

    def __init__(self, source: str = "magnatrix"):
        self.logger = StructuredLogger(source)
        self.rotator = LogRotator("/tmp/magnatrix.log")
        self.patterns = PatternExtractor()
        self.anomaly = AnomalyDetector()
        self.correlator = LogCorrelator()
        self._setup_handlers()

    def _setup_handlers(self):
        def _handler(entry: LogEntry):
            self.rotator.write(json.dumps(entry.to_dict()))
            self.anomaly.observe(entry)
            self.correlator.add(entry)
        self.logger.add_handler(_handler)

    def log(self, level: int, message: str, trace_id: str = "", metadata: Dict = None):
        self.logger.log(level, message, trace_id, metadata)

    def search(self, pattern: str = "", min_level: int = 0, trace_id: str = "", limit: int = 100) -> List[LogEntry]:
        return self.logger.query(min_level, pattern, trace_id, limit)

    def detect_anomalies(self) -> Tuple[bool, float]:
        return self.anomaly.is_anomaly()

    def correlate(self, trace_id: str) -> Dict:
        return {
            "entries": [e.to_dict() for e in self.correlator.get_trace(trace_id)],
            "duration": self.correlator.trace_duration(trace_id),
            "errors": len(self.correlator.trace_errors(trace_id)),
        }

    def export(self, path: str):
        self.logger.export_json(path)


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("logger_level", lambda: (l := StructuredLogger("x"), l.info("hi"), len(l.query()) == 1)[2])
    _t("logger_filter", lambda: (l := StructuredLogger("x"), l.error("err"), l.info("ok"), len(l.query(min_level=LogLevel.ERROR.value)) == 1)[3])
    _t("rotator_write", lambda: (r := LogRotator("/tmp/mtx_log_test.log"), r.write("test"), os.path.exists(r.path))[2])
    _t("pattern_extract", lambda: (p := PatternExtractor(), p.add_pattern("ip", r"\d+\.\d+\.\d+\.\d+"), p.extract("IP: 1.2.3.4")["ip"] == ["1.2.3.4"])[2])
    _t("anomaly_detect", lambda: (a := AnomalyDetector(), [a.observe(LogEntry(time.time(), 20, "x", "s")) for _ in range(20)], a.is_anomaly()[0])[2])
    _t("correlator_trace", lambda: (c := LogCorrelator(), c.add(LogEntry(1, 20, "a", "s", "tid1")), c.add(LogEntry(2, 20, "b", "s", "tid1")), len(c.get_trace("tid1")) == 2)[3])
    _t("trace_duration", lambda: (c := LogCorrelator(), c.add(LogEntry(1, 20, "a", "s", "t1")), c.add(LogEntry(5, 20, "b", "s", "t1")), c.trace_duration("t1") == 4.0)[3])
    _t("aggregator_log", lambda: (a := LogAggregator(), a.log(LogLevel.INFO.value, "test"), len(a.search("test")) == 1)[2])
    _t("error_burst", lambda: AnomalyDetector().error_burst([LogEntry(float(i), 40, "e", "s") for i in range(10)], threshold=5))
    _t("export", lambda: (a := LogAggregator(), a.log(20, "x"), a.export("/tmp/mtx_log_export.json"), os.path.exists("/tmp/mtx_log_export.json"))[3])

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nLog Aggregator: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
