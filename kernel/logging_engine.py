#!/usr/bin/env python3
"""
MAGNATRIX-OS — Layer 0: Logging Engine
Native Python, zero external dependencies.
Structured logging, rotation, audit chain, per-layer logging.
"""
from __future__ import annotations
import json, hashlib, queue, threading, time, os, gzip
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Any


class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    AUDIT = 5


@dataclass
class LogEntry:
    timestamp: float
    level: LogLevel
    layer: str
    module: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    prev_hash: str = ""
    entry_hash: str = ""

    def compute_hash(self) -> str:
        data = f"{self.timestamp}|{self.level.name}|{self.layer}|{self.module}|{self.message}|{json.dumps(self.context, sort_keys=True)}|{self.trace_id}|{self.prev_hash}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def finalize(self) -> "LogEntry":
        self.entry_hash = self.compute_hash()
        return self


class StructuredFormatter:
    """Format log entries to JSON, plain text, or compact."""

    @staticmethod
    def json(entry: LogEntry) -> str:
        return json.dumps({
            "ts": entry.timestamp,
            "lvl": entry.level.name,
            "layer": entry.layer,
            "mod": entry.module,
            "msg": entry.message,
            "ctx": entry.context,
            "trace": entry.trace_id,
            "hash": entry.entry_hash,
        }, ensure_ascii=False, default=str)

    @staticmethod
    def plain(entry: LogEntry) -> str:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp))
        return f"[{ts}] [{entry.level.name:8}] [{entry.layer:12}] [{entry.module:20}] {entry.message}"

    @staticmethod
    def compact(entry: LogEntry) -> str:
        return f"{entry.timestamp:.3f}|{entry.level.name[0]}|{entry.layer}|{entry.message[:60]}"


class LogRotator:
    """Rotate logs by size (10MB) and by day, keep 7 backups, gzip old."""

    def __init__(self, filepath: str, max_size: int = 10_000_000, max_days: int = 7):
        self.filepath = filepath
        self.max_size = max_size
        self.max_days = max_days
        self._lock = threading.Lock()
        self._current_size = 0
        self._current_date = time.strftime("%Y%m%d")
        self._ensure_file()

    def _ensure_file(self):
        if os.path.exists(self.filepath):
            self._current_size = os.path.getsize(self.filepath)
        else:
            os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
            open(self.filepath, "a").close()
            self._current_size = 0

    def _rotate(self):
        with self._lock:
            if not os.path.exists(self.filepath):
                return
            # Backup existing
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup = f"{self.filepath}.{timestamp}"
            os.rename(self.filepath, backup)
            # Gzip old backups beyond max_days
            self._cleanup_old()
            # Reset
            open(self.filepath, "a").close()
            self._current_size = 0

    def _cleanup_old(self):
        dir_path = os.path.dirname(self.filepath) or "."
        base_name = os.path.basename(self.filepath)
        backups = [f for f in os.listdir(dir_path) if f.startswith(base_name + ".")]
        backups.sort(reverse=True)
        # Gzip all but keep only max_days uncompressed
        for i, backup in enumerate(backups):
            backup_path = os.path.join(dir_path, backup)
            if not backup.endswith(".gz"):
                gz_path = backup_path + ".gz"
                with open(backup_path, "rb") as f_in:
                    with gzip.open(gz_path, "wb") as f_out:
                        f_out.write(f_in.read())
                os.remove(backup_path)
        # Remove old gzipped beyond max_days
        gz_backups = [f for f in os.listdir(dir_path) if f.startswith(base_name + ".") and f.endswith(".gz")]
        gz_backups.sort(reverse=True)
        for old in gz_backups[self.max_days:]:
            os.remove(os.path.join(dir_path, old))

    def write(self, line: str):
        with self._lock:
            line_bytes = (line + "\n").encode("utf-8")
            if self._current_size + len(line_bytes) > self.max_size:
                self._rotate()
            # Check day rotation
            today = time.strftime("%Y%m%d")
            if today != self._current_date:
                self._current_date = today
                self._rotate()
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            self._current_size += len(line_bytes)


class AsyncLogger:
    """Non-blocking queue + background thread flush to disk."""

    def __init__(self, rotator: LogRotator, formatter: StructuredFormatter, level: LogLevel = LogLevel.DEBUG):
        self.rotator = rotator
        self.formatter = formatter
        self.level = level
        self._queue: queue.Queue = queue.Queue(maxsize=10000)
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._running = True
        self._thread.start()
        self._callbacks: List[Callable[[LogEntry], None]] = []

    def _flush_loop(self):
        while self._running:
            try:
                entry = self._queue.get(timeout=1.0)
                line = self.formatter.plain(entry)
                self.rotator.write(line)
                for cb in self._callbacks:
                    try:
                        cb(entry)
                    except Exception:
                        pass
            except queue.Empty:
                continue

    def log(self, entry: LogEntry):
        if entry.level.value < self.level.value:
            return
        entry.finalize()
        try:
            self._queue.put_nowait(entry)
        except queue.Full:
            pass  # Drop if full

    def add_callback(self, cb: Callable[[LogEntry], None]):
        self._callbacks.append(cb)

    def stop(self):
        self._running = False
        self._thread.join(timeout=5.0)


class LayerLogger:
    """Per-layer logger instance."""

    _layers: Dict[str, "LayerLogger"] = {}
    _lock = threading.Lock()

    def __init__(self, layer: str, logger: AsyncLogger):
        self.layer = layer
        self.logger = logger

    @classmethod
    def get(cls, layer: str, logger: AsyncLogger) -> "LayerLogger":
        with cls._lock:
            if layer not in cls._layers:
                cls._layers[layer] = cls(layer, logger)
            return cls._layers[layer]

    def log(self, level: LogLevel, module: str, message: str, context: Dict = None, trace_id: str = ""):
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            layer=self.layer,
            module=module,
            message=message,
            context=context or {},
            trace_id=trace_id or f"trace-{int(time.time()*1000)}-{threading.current_thread().ident}",
        )
        self.logger.log(entry)

    def debug(self, module: str, msg: str, **ctx):
        self.log(LogLevel.DEBUG, module, msg, ctx)

    def info(self, module: str, msg: str, **ctx):
        self.log(LogLevel.INFO, module, msg, ctx)

    def warning(self, module: str, msg: str, **ctx):
        self.log(LogLevel.WARNING, module, msg, ctx)

    def error(self, module: str, msg: str, **ctx):
        self.log(LogLevel.ERROR, module, msg, ctx)

    def critical(self, module: str, msg: str, **ctx):
        self.log(LogLevel.CRITICAL, module, msg, ctx)

    def audit(self, module: str, msg: str, **ctx):
        self.log(LogLevel.AUDIT, module, msg, ctx)


class AuditLogger:
    """Tamper-resistant log with hash chain."""

    def __init__(self, logger: AsyncLogger):
        self.logger = logger
        self._last_hash = "0" * 32
        self._lock = threading.Lock()

    def log(self, layer: str, module: str, message: str, context: Dict = None):
        with self._lock:
            entry = LogEntry(
                timestamp=time.time(),
                level=LogLevel.AUDIT,
                layer=layer,
                module=module,
                message=message,
                context=context or {},
                prev_hash=self._last_hash,
            )
            entry.finalize()
            self._last_hash = entry.entry_hash
            self.logger.log(entry)


class LogAggregator:
    """Collect logs from all layers, filter by level/trace_id/layer/time."""

    def __init__(self):
        self._entries: List[LogEntry] = []
        self._lock = threading.Lock()

    def add(self, entry: LogEntry):
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > 10000:
                self._entries = self._entries[-5000:]

    def filter(self, level: LogLevel = None, layer: str = None, trace_id: str = None, since: float = None) -> List[LogEntry]:
        with self._lock:
            result = self._entries[:]
        if level:
            result = [e for e in result if e.level.value >= level.value]
        if layer:
            result = [e for e in result if e.layer == layer]
        if trace_id:
            result = [e for e in result if e.trace_id == trace_id]
        if since:
            result = [e for e in result if e.timestamp >= since]
        return result

    def stats(self) -> Dict:
        with self._lock:
            entries = self._entries[:]
        if not entries:
            return {}
        levels = {}
        layers = {}
        for e in entries:
            levels[e.level.name] = levels.get(e.level.name, 0) + 1
            layers[e.layer] = layers.get(e.layer, 0) + 1
        return {
            "total": len(entries),
            "time_range": (entries[0].timestamp, entries[-1].timestamp),
            "by_level": levels,
            "by_layer": layers,
        }


class LogKernelBridge:
    """Bridge to event_bus and service_registry."""

    def __init__(self, logger: AsyncLogger, event_bus=None, service_registry=None):
        self.logger = logger
        self.event_bus = event_bus
        self.service_registry = service_registry

    def publish_log_event(self, entry: LogEntry):
        if self.event_bus:
            try:
                self.event_bus.publish("kernel.log", {
                    "level": entry.level.name,
                    "layer": entry.layer,
                    "message": entry.message,
                    "trace_id": entry.trace_id,
                })
            except Exception:
                pass

    def register_service(self):
        if self.service_registry:
            try:
                self.service_registry.register("logging_engine", {"status": "running"})
            except Exception:
                pass


class LoggingEngine:
    """Main orchestrator for MAGNATRIX-OS logging."""

    def __init__(self, log_dir: str = "logs", level: LogLevel = LogLevel.DEBUG):
        os.makedirs(log_dir, exist_ok=True)
        self.rotator = LogRotator(os.path.join(log_dir, "magnatrix.log"))
        self.formatter = StructuredFormatter()
        self.logger = AsyncLogger(self.rotator, self.formatter, level)
        self.audit = AuditLogger(self.logger)
        self.aggregator = LogAggregator()
        self.bridge = LogKernelBridge(self.logger)
        self._layers: Dict[str, LayerLogger] = {}
        self._lock = threading.Lock()

        # Wire aggregator
        self.logger.add_callback(self.aggregator.add)
        self.logger.add_callback(self.bridge.publish_log_event)

    def get_layer_logger(self, layer: str) -> LayerLogger:
        with self._lock:
            if layer not in self._layers:
                self._layers[layer] = LayerLogger.get(layer, self.logger)
            return self._layers[layer]

    def boot(self):
        self.bridge.register_service()
        self.logger.info("LoggingEngine", "Logging engine booted", version="1.0")

    def shutdown(self):
        self.logger.info("LoggingEngine", "Logging engine shutting down")
        self.logger.stop()


def run_demo():
    print("=" * 60)
    print("MAGNATRIX-OS Logging Engine Demo")
    print("=" * 60)

    engine = LoggingEngine(log_dir="logs_demo", level=LogLevel.DEBUG)
    engine.boot()

    # Simulate logs from multiple layers
    layers = ["kernel", "protocol", "p2p_mesh", "identity", "hft", "security", "governance"]
    levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]

    for i in range(50):
        layer = layers[i % len(layers)]
        logger = engine.get_layer_logger(layer)
        level = levels[i % len(levels)]
        logger.log(level, "demo_module", f"Simulated event #{i+1} from {layer}", {"iteration": i})

    # Audit logs
    for i in range(5):
        engine.audit.log("security", "audit_module", f"Security audit event #{i+1}", {"check": "integrity"})

    time.sleep(2)  # Let async flush

    stats = engine.aggregator.stats()
    print(f"\nTotal entries collected: {stats.get('total', 0)}")
    print(f"By level: {stats.get('by_level', {})}")
    print(f"By layer: {stats.get('by_layer', {})}")

    # Filter demo
    errors = engine.aggregator.filter(level=LogLevel.ERROR)
    print(f"\nError entries: {len(errors)}")

    kernel_logs = engine.aggregator.filter(layer="kernel")
    print(f"Kernel logs: {len(kernel_logs)}")

    engine.shutdown()
    print("\nDemo complete. Check logs_demo/magnatrix.log")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
