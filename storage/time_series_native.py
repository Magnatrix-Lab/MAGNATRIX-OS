#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Time-Series Database (Layer 8 Extension)
Columnar storage for metrics and trading data with downsampling,
OHLCV aggregation, and time-range queries.
================================================================================
Zero-dependency TSDB using memory + file-backed segments.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


# =============================================================================
# Constants
# =============================================================================
DEFAULT_TSDB_DIR = "/tmp/magnatrix_tsdb"
DEFAULT_RETENTION_SEC = 86400 * 30  # 30 days
DOWNSAMPLE_RANGES = ["1m", "5m", "15m", "1h", "4h", "1d"]


# =============================================================================
# Data Types
# =============================================================================
@dataclass
class DataPoint:
    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metric: str = ""


@dataclass
class OHLCV:
    """Open-High-Low-Close-Volume candle."""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class TimeRange:
    start: float
    end: float

    @property
    def duration_sec(self) -> float:
        return self.end - self.start


# =============================================================================
# Downsampler
# =============================================================================
class Downsampler:
    """Aggregate raw points into lower resolution buckets."""

    INTERVALS = {
        "1s": 1,
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }

    @classmethod
    def bucket_timestamp(cls, ts: float, interval_sec: int) -> float:
        return (ts // interval_sec) * interval_sec

    @classmethod
    def downsample(cls, points: List[DataPoint], interval: str) -> List[DataPoint]:
        if not points:
            return []
        interval_sec = cls.INTERVALS.get(interval, 60)
        buckets: Dict[float, List[float]] = {}
        for p in points:
            bucket = cls.bucket_timestamp(p.timestamp, interval_sec)
            buckets.setdefault(bucket, []).append(p.value)
        result = []
        for bucket in sorted(buckets):
            vals = buckets[bucket]
            result.append(DataPoint(
                timestamp=bucket,
                value=sum(vals) / len(vals),
                metric=points[0].metric,
            ))
        return result

    @classmethod
    def ohlcv(cls, points: List[DataPoint], interval: str) -> List[OHLCV]:
        if not points:
            return []
        interval_sec = cls.INTERVALS.get(interval, 60)
        buckets: Dict[float, List[float]] = {}
        for p in points:
            bucket = cls.bucket_timestamp(p.timestamp, interval_sec)
            buckets.setdefault(bucket, []).append(p.value)
        result = []
        for bucket in sorted(buckets):
            vals = buckets[bucket]
            result.append(OHLCV(
                timestamp=bucket,
                open=vals[0],
                high=max(vals),
                low=min(vals),
                close=vals[-1],
                volume=len(vals),
            ))
        return result


# =============================================================================
# Columnar Segment
# =============================================================================
class ColumnarSegment:
    """Store time-series data in columnar format per metric."""

    def __init__(self, metric: str, start_time: float, directory: str) -> None:
        self.metric = metric
        self.start_time = start_time
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._timestamps: List[float] = []
        self._values: List[float] = []
        self._tags_list: List[str] = []
        self._lock = threading.Lock()
        self._dirty = False

    def insert(self, point: DataPoint) -> bool:
        with self._lock:
            self._timestamps.append(point.timestamp)
            self._values.append(point.value)
            self._tags_list.append(json.dumps(point.tags, sort_keys=True))
            self._dirty = True
        return True

    def query(self, time_range: TimeRange, tags_filter: Optional[Dict[str, str]] = None) -> List[DataPoint]:
        result = []
        with self._lock:
            for i in range(len(self._timestamps)):
                if time_range.start <= self._timestamps[i] <= time_range.end:
                    if tags_filter:
                        tags = json.loads(self._tags_list[i])
                        if not all(tags.get(k) == v for k, v in tags_filter.items()):
                            continue
                    result.append(DataPoint(
                        timestamp=self._timestamps[i],
                        value=self._values[i],
                        metric=self.metric,
                        tags=json.loads(self._tags_list[i]),
                    ))
        return result

    def flush(self) -> None:
        with self._lock:
            if not self._dirty:
                return
            path = self.dir / f"{self.metric}_{int(self.start_time)}.bin"
            with open(path, "wb") as f:
                # Header: count (4 bytes)
                f.write(struct.pack("<I", len(self._timestamps)))
                # Timestamps as float64
                for t in self._timestamps:
                    f.write(struct.pack("<d", t))
                # Values as float64
                for v in self._values:
                    f.write(struct.pack("<d", v))
                # Tags as length-prefixed JSON
                for tags in self._tags_list:
                    tbytes = tags.encode("utf-8")
                    f.write(struct.pack("<I", len(tbytes)))
                    f.write(tbytes)
            self._dirty = False

    @classmethod
    def load(cls, metric: str, start_time: float, directory: str) -> "ColumnarSegment":
        seg = cls(metric, start_time, directory)
        path = seg.dir / f"{metric}_{int(start_time)}.bin"
        if not path.exists():
            return seg
        with open(path, "rb") as f:
            count = struct.unpack("<I", f.read(4))[0]
            for _ in range(count):
                seg._timestamps.append(struct.unpack("<d", f.read(8))[0])
            for _ in range(count):
                seg._values.append(struct.unpack("<d", f.read(8))[0])
            for _ in range(count):
                tlen = struct.unpack("<I", f.read(4))[0]
                seg._tags_list.append(f.read(tlen).decode("utf-8"))
        return seg

    def __len__(self) -> int:
        return len(self._timestamps)


# =============================================================================
# Retention Manager
# =============================================================================
class RetentionManager:
    """Enforce retention policies and compaction."""

    def __init__(self, retention_sec: float = DEFAULT_RETENTION_SEC) -> None:
        self.retention_sec = retention_sec

    def should_retain(self, timestamp: float) -> bool:
        return (time.time() - timestamp) <= self.retention_sec

    def prune_segments(self, segments: List[ColumnarSegment]) -> List[ColumnarSegment]:
        return [s for s in segments if self.should_retain(s.start_time)]


# =============================================================================
# Aggregation Engine
# =============================================================================
class AggregationEngine:
    """Compute aggregates over time ranges."""

    @staticmethod
    def sum(points: List[DataPoint]) -> float:
        return sum(p.value for p in points)

    @staticmethod
    def avg(points: List[DataPoint]) -> float:
        vals = [p.value for p in points]
        return sum(vals) / len(vals) if vals else 0.0

    @staticmethod
    def min(points: List[DataPoint]) -> float:
        return min((p.value for p in points), default=0.0)

    @staticmethod
    def max(points: List[DataPoint]) -> float:
        return max((p.value for p in points), default=0.0)

    @staticmethod
    def count(points: List[DataPoint]) -> int:
        return len(points)

    @staticmethod
    def percentile(points: List[DataPoint], p: float) -> float:
        vals = sorted(p.value for p in points)
        if not vals:
            return 0.0
        k = (len(vals) - 1) * p
        f = int(k)
        c = f + 1 if f + 1 < len(vals) else f
        return vals[f] + (k - f) * (vals[c] - vals[f]) if c != f else vals[f]

    @staticmethod
    def rate(points: List[DataPoint], interval_sec: float = 60.0) -> float:
        """Calculate rate of change per interval."""
        if len(points) < 2:
            return 0.0
        total_change = points[-1].value - points[0].value
        total_time = points[-1].timestamp - points[0].timestamp
        return (total_change / total_time) * interval_sec if total_time > 0 else 0.0


# =============================================================================
# TSDB Engine
# =============================================================================
class TSDBEngine:
    """Top-level time-series database."""

    def __init__(self, db_dir: str = DEFAULT_TSDB_DIR, retention_sec: float = DEFAULT_RETENTION_SEC) -> None:
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.retention = RetentionManager(retention_sec)
        self._segments: Dict[str, List[ColumnarSegment]] = {}
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[DataPoint], None]] = []
        self._downsampled: Dict[str, Dict[str, List[DataPoint]]] = {}  # metric -> interval -> points
        self._load_segments()

    def _load_segments(self) -> None:
        for p in self.db_dir.glob("*.bin"):
            parts = p.stem.split("_")
            if len(parts) >= 2:
                metric = "_".join(parts[:-1])
                start_time = float(parts[-1])
                seg = ColumnarSegment.load(metric, start_time, str(self.db_dir))
                with self._lock:
                    self._segments.setdefault(metric, []).append(seg)

    def _get_or_create_segment(self, metric: str, timestamp: float) -> ColumnarSegment:
        """Get segment for timestamp, creating new one if needed."""
        with self._lock:
            segs = self._segments.setdefault(metric, [])
            # Find segment covering this timestamp (1 hour buckets)
            bucket_start = (timestamp // 3600) * 3600
            for seg in segs:
                if seg.start_time == bucket_start:
                    return seg
            # Create new segment
            seg = ColumnarSegment(metric, bucket_start, str(self.db_dir))
            segs.append(seg)
            return seg

    def on_insert(self, callback: Callable[[DataPoint], None]) -> None:
        self._callbacks.append(callback)

    def insert(self, metric: str, value: float, timestamp: Optional[float] = None, tags: Optional[Dict[str, str]] = None) -> bool:
        ts = timestamp or time.time()
        point = DataPoint(timestamp=ts, value=value, metric=metric, tags=tags or {})
        seg = self._get_or_create_segment(metric, ts)
        seg.insert(point)
        for cb in self._callbacks:
            cb(point)
        return True

    def query(self, metric: str, start: float, end: float, tags: Optional[Dict[str, str]] = None, downsample: Optional[str] = None) -> List[DataPoint]:
        tr = TimeRange(start=start, end=end)
        all_points: List[DataPoint] = []
        with self._lock:
            segs = self._segments.get(metric, [])
        for seg in segs:
            points = seg.query(tr, tags)
            all_points.extend(points)
        all_points.sort(key=lambda p: p.timestamp)
        if downsample:
            return Downsampler.downsample(all_points, downsample)
        return all_points

    def query_ohlcv(self, metric: str, start: float, end: float, interval: str = "1m") -> List[OHLCV]:
        tr = TimeRange(start=start, end=end)
        all_points: List[DataPoint] = []
        with self._lock:
            segs = self._segments.get(metric, [])
        for seg in segs:
            points = seg.query(tr)
            all_points.extend(points)
        all_points.sort(key=lambda p: p.timestamp)
        return Downsampler.ohlcv(all_points, interval)

    def aggregate(self, metric: str, start: float, end: float, func: str = "avg") -> float:
        points = self.query(metric, start, end)
        if func == "sum":
            return AggregationEngine.sum(points)
        elif func == "avg":
            return AggregationEngine.avg(points)
        elif func == "min":
            return AggregationEngine.min(points)
        elif func == "max":
            return AggregationEngine.max(points)
        elif func == "count":
            return float(AggregationEngine.count(points))
        elif func == "rate":
            return AggregationEngine.rate(points)
        return 0.0

    def flush(self) -> None:
        with self._lock:
            for segs in self._segments.values():
                for seg in segs:
                    seg.flush()

    def prune(self) -> int:
        """Remove segments beyond retention."""
        removed = 0
        with self._lock:
            for metric, segs in list(self._segments.items()):
                kept = self.retention.prune_segments(segs)
                removed += len(segs) - len(kept)
                self._segments[metric] = kept
        return removed

    def metrics(self) -> List[str]:
        with self._lock:
            return sorted(self._segments.keys())

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total_points = sum(sum(len(s) for s in segs) for segs in self._segments.values())
            total_metrics = len(self._segments)
        return {
            "metrics": total_metrics,
            "points": total_points,
            "segments": sum(len(segs) for segs in self._segments.values()),
        }

    def shutdown(self) -> None:
        self.flush()

    def __enter__(self) -> TSDBEngine:
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown()


# =============================================================================
# TSDB Kernel Bridge
# =============================================================================
class TSDBKernelBridge:
    def __init__(self, engine: TSDBEngine, event_bus: Any = None) -> None:
        self.engine = engine
        self.bus = event_bus
        engine.on_insert(self._on_insert)

    def _on_insert(self, point: DataPoint) -> None:
        if self.bus:
            self.bus.publish("tsdb.insert", {
                "metric": point.metric,
                "timestamp": point.timestamp,
                "value": point.value,
            })


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS TSDB Demo")
    print("=" * 60)
    tsdb = TSDBEngine("/tmp/magnatrix_demo_tsdb")

    # Insert trading data
    base_time = time.time() - 3600
    for i in range(100):
        price = 50000 + (i % 20) * 10
        tsdb.insert("btc_price", price, base_time + i * 60, {"exchange": "binance", "pair": "BTCUSDT"})

    print(f"Inserted {tsdb.stats()['points']} points")

    # Query raw
    points = tsdb.query("btc_price", base_time, base_time + 3600)
    print(f"Raw query: {len(points)} points")

    # OHLCV
    candles = tsdb.query_ohlcv("btc_price", base_time, base_time + 3600, "5m")
    print(f"OHLCV (5m): {len(candles)} candles")
    if candles:
        print(f"  First candle: O={candles[0].open} H={candles[0].high} L={candles[0].low} C={candles[0].close}")

    # Aggregate
    avg_price = tsdb.aggregate("btc_price", base_time, base_time + 3600, "avg")
    print(f"Average price: {avg_price:.2f}")

    # Downsample
    ds = tsdb.query("btc_price", base_time, base_time + 3600, downsample="15m")
    print(f"Downsampled (15m): {len(ds)} points")

    tsdb.shutdown()
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
