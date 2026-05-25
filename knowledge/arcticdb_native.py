"""
MAGNATRIX-OS Layer 5 — ArcticDB Native (Bagian 1)
Time-Series Storage Engine berbasis pattern ArcticDB (man-group/ArcticDB)
Pure Python, standard library + asyncio, zero external dependencies.

Bagian 1: Chunk, ChunkStore, SymbolRegistry, TimeSeriesEngine, S3StorageStub
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

# ═══════════════════════════════════════════════════════════════════════════════
# 1. CHUNK — Unit dasar penyimpanan time-series
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Chunk:
    """Unit penyimpanan time-series: blok data dengan metadata temporal."""
    data: List[Dict[str, Any]] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    symbol: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    chunk_id: str = field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:12]}")
    created_at: float = field(default_factory=time.time)
    row_count: int = 0
    byte_size: int = 0

    def __post_init__(self) -> None:
        if self.data:
            self.row_count = len(self.data)
            self.byte_size = len(json.dumps(self.data, default=str).encode())
            if not self.start_time and self.data:
                self.start_time = self._extract_time(self.data[0])
            if not self.end_time and self.data:
                self.end_time = self._extract_time(self.data[-1])

    @staticmethod
    def _extract_time(row: Dict[str, Any]) -> float:
        """Ekstrak timestamp dari row — support float, int, ISO string."""
        ts = row.get("timestamp", row.get("time", row.get("ts", 0)))
        if isinstance(ts, (int, float)):
            return float(ts)
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return dt.timestamp()
            except ValueError:
                return 0.0
        return 0.0

    def append(self, row: Dict[str, Any]) -> None:
        """Append single row dan update bounds."""
        self.data.append(row)
        self.row_count += 1
        ts = self._extract_time(row)
        if ts > 0:
            if self.start_time == 0 or ts < self.start_time:
                self.start_time = ts
            if ts > self.end_time:
                self.end_time = ts
        self.byte_size = len(json.dumps(self.data, default=str).encode())

    def split(self, max_rows: int = 1000) -> List["Chunk"]:
        """Split chunk jika melebihi max_rows."""
        if self.row_count <= max_rows:
            return [self]
        chunks: List[Chunk] = []
        for i in range(0, len(self.data), max_rows):
            subset = self.data[i:i + max_rows]
            chunk = Chunk(
                data=subset,
                symbol=self.symbol,
                metadata={**self.metadata, "parent_chunk": self.chunk_id},
                version=self.version,
            )
            chunks.append(chunk)
        return chunks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "symbol": self.symbol,
            "version": self.version,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "row_count": self.row_count,
            "byte_size": self.byte_size,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"Chunk({self.symbol}, rows={self.row_count}, {self.start_time:.0f}→{self.end_time:.0f})"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CHUNK STORE — Append-only storage dengan compaction
# ═══════════════════════════════════════════════════════════════════════════════

class ChunkStore:
    """Append-only chunk storage engine."""

    def __init__(self, max_chunk_rows: int = 1000, max_chunk_bytes: int = 1_000_000) -> None:
        self.chunks: Dict[str, List[Chunk]] = {}  # symbol -> list of chunks
        self.max_chunk_rows = max_chunk_rows
        self.max_chunk_bytes = max_chunk_bytes
        self.stats: Dict[str, Any] = {"writes": 0, "reads": 0, "splits": 0, "compactions": 0}

    def write(self, symbol: str, rows: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Write rows ke symbol — auto-split jika perlu."""
        if symbol not in self.chunks:
            self.chunks[symbol] = []

        chunk = Chunk(data=[], symbol=symbol, metadata=metadata or {})
        written_chunks: List[Chunk] = []

        for row in rows:
            chunk.append(row)
            if chunk.row_count >= self.max_chunk_rows or chunk.byte_size >= self.max_chunk_bytes:
                self.chunks[symbol].append(chunk)
                written_chunks.append(chunk)
                chunk = Chunk(data=[], symbol=symbol, metadata=metadata or {})

        if chunk.row_count > 0:
            self.chunks[symbol].append(chunk)
            written_chunks.append(chunk)

        self.stats["writes"] += 1
        return written_chunks

    def read(self, symbol: str, start_time: Optional[float] = None,
             end_time: Optional[float] = None) -> Iterator[Dict[str, Any]]:
        """Read rows by time range."""
        self.stats["reads"] += 1
        for chunk in self.chunks.get(symbol, []):
            if start_time and chunk.end_time < start_time:
                continue
            if end_time and chunk.start_time > end_time:
                continue
            for row in chunk.data:
                ts = Chunk._extract_time(row)
                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue
                yield row

    def get_chunks(self, symbol: str) -> List[Chunk]:
        return list(self.chunks.get(symbol, []))

    def compact(self, symbol: str, target_chunk_size: int = 1000) -> int:
        """Compact chunks — merge small chunks into larger ones."""
        chunks = self.chunks.get(symbol, [])
        if not chunks:
            return 0

        # Sort by start_time
        chunks.sort(key=lambda c: c.start_time)
        merged: List[Chunk] = []
        current = Chunk(data=[], symbol=symbol)

        for chunk in chunks:
            if current.row_count + chunk.row_count <= target_chunk_size:
                for row in chunk.data:
                    current.append(row)
            else:
                if current.row_count > 0:
                    merged.append(current)
                current = Chunk(data=list(chunk.data), symbol=symbol)

        if current.row_count > 0:
            merged.append(current)

        self.chunks[symbol] = merged
        self.stats["compactions"] += 1
        return len(merged)

    def garbage_collect(self, symbol: str, before_version: int) -> int:
        """Stub: remove chunks older than version (placeholder)."""
        # In real ArcticDB: remove unreferenced old versions
        return 0

    def list_symbols(self) -> List[str]:
        return list(self.chunks.keys())

    def symbol_stats(self, symbol: str) -> Dict[str, Any]:
        chunks = self.chunks.get(symbol, [])
        total_rows = sum(c.row_count for c in chunks)
        total_bytes = sum(c.byte_size for c in chunks)
        return {
            "symbol": symbol,
            "chunks": len(chunks),
            "total_rows": total_rows,
            "total_bytes": total_bytes,
            "time_range": (min(c.start_time for c in chunks) if chunks else 0,
                           max(c.end_time for c in chunks) if chunks else 0),
        }

    def __repr__(self) -> str:
        return f"ChunkStore(symbols={len(self.chunks)}, stats={self.stats})"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SYMBOL REGISTRY — Manajemen symbol dan metadata
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SymbolInfo:
    """Metadata untuk sebuah symbol."""
    name: str
    created_at: float = field(default_factory=time.time)
    last_modified: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    versions: List[int] = field(default_factory=lambda: [1])
    current_version: int = 1
    row_count: int = 0
    schema: Optional[Dict[str, str]] = None

    def bump_version(self) -> int:
        self.current_version += 1
        self.versions.append(self.current_version)
        self.last_modified = time.time()
        return self.current_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "versions": self.versions,
            "current_version": self.current_version,
            "row_count": self.row_count,
            "schema": self.schema,
            "metadata": self.metadata,
        }


class SymbolRegistry:
    """Registry untuk symbols — ticker names, metadata, versioning."""

    def __init__(self) -> None:
        self.symbols: Dict[str, SymbolInfo] = {}
        self.index: Dict[str, Set[str]] = {}  # tag -> symbols

    def register(self, name: str, metadata: Optional[Dict[str, Any]] = None,
                 schema: Optional[Dict[str, str]] = None) -> SymbolInfo:
        """Register new symbol."""
        if name in self.symbols:
            info = self.symbols[name]
            if metadata:
                info.metadata.update(metadata)
            if schema:
                info.schema = schema
            info.last_modified = time.time()
            return info

        info = SymbolInfo(name=name, metadata=metadata or {}, schema=schema)
        self.symbols[name] = info
        return info

    def unregister(self, name: str) -> None:
        self.symbols.pop(name, None)
        for tag, symbols in self.index.items():
            symbols.discard(name)

    def get(self, name: str) -> Optional[SymbolInfo]:
        return self.symbols.get(name)

    def list_all(self) -> List[str]:
        return list(self.symbols.keys())

    def bump_version(self, name: str) -> int:
        info = self.symbols.get(name)
        if info:
            return info.bump_version()
        return 0

    def tag_symbol(self, name: str, tag: str) -> None:
        if name not in self.symbols:
            return
        self.index.setdefault(tag, set()).add(name)

    def find_by_tag(self, tag: str) -> List[str]:
        return list(self.index.get(tag, set()))

    def update_row_count(self, name: str, count: int) -> None:
        info = self.symbols.get(name)
        if info:
            info.row_count = count
            info.last_modified = time.time()

    def __repr__(self) -> str:
        return f"SymbolRegistry(symbols={len(self.symbols)})"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. TIME-SERIES ENGINE — OHLCV, trades, quotes, resampling
# ═══════════════════════════════════════════════════════════════════════════════

class TimeSeriesEngine:
    """Engine untuk store dan query time-series data."""

    RESAMPLE_MAP = {
        "1min": 60,
        "5min": 300,
        "15min": 900,
        "1H": 3600,
        "4H": 14400,
        "1D": 86400,
    }

    def __init__(self, chunk_store: ChunkStore, symbol_registry: SymbolRegistry) -> None:
        self.store = chunk_store
        self.registry = symbol_registry
        self.caches: Dict[str, List[Dict[str, Any]]] = {}  # symbol -> recent rows cache
        self.cache_size = 1000

    def store_ticks(self, symbol: str, ticks: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Store tick data (trades/quotes)."""
        self.registry.register(symbol, metadata=metadata)
        chunks = self.store.write(symbol, ticks, metadata)
        self.registry.update_row_count(symbol, self.store.symbol_stats(symbol)["total_rows"])
        # Update cache
        cache = self.caches.setdefault(symbol, [])
        cache.extend(ticks)
        if len(cache) > self.cache_size * 2:
            self.caches[symbol] = cache[-self.cache_size:]
        return chunks

    def store_ohlcv(self, symbol: str, ohlcv: List[Dict[str, Any]]) -> List[Chunk]:
        """Store OHLCV candle data."""
        return self.store_ticks(symbol, ohlcv, metadata={"type": "ohlcv"})

    def query_range(self, symbol: str, start: float, end: float) -> List[Dict[str, Any]]:
        """Query data dalam time range."""
        return list(self.store.read(symbol, start, end))

    def query_latest(self, symbol: str, n: int = 100) -> List[Dict[str, Any]]:
        """Query n latest rows."""
        cache = self.caches.get(symbol, [])
        if len(cache) >= n:
            return cache[-n:]
        # Fallback: read all and take last n
        all_rows = list(self.store.read(symbol))
        return all_rows[-n:] if len(all_rows) >= n else all_rows

    def resample(self, symbol: str, interval: str, start: Optional[float] = None,
                 end: Optional[float] = None) -> List[Dict[str, Any]]:
        """Resample ticks ke interval (1min, 5min, 1H, 1D)."""
        seconds = self.RESAMPLE_MAP.get(interval, 60)
        rows = list(self.store.read(symbol, start, end))
        if not rows:
            return []

        # Sort by time
        rows.sort(key=lambda r: Chunk._extract_time(r))

        buckets: Dict[int, List[Dict[str, Any]]] = {}
        for row in rows:
            ts = Chunk._extract_time(row)
            bucket_key = int(ts // seconds) * seconds
            buckets.setdefault(bucket_key, []).append(row)

        candles: List[Dict[str, Any]] = []
        for bucket_time in sorted(buckets.keys()):
            bucket = buckets[bucket_time]
            prices = [r.get("price", r.get("close", 0)) for r in bucket if any(k in r for k in ("price", "close"))]
            volumes = [r.get("volume", r.get("vol", 0)) for r in bucket]

            if prices:
                candle = {
                    "timestamp": bucket_time,
                    "open": prices[0],
                    "high": max(prices),
                    "low": min(prices),
                    "close": prices[-1],
                    "volume": sum(volumes) if volumes else 0,
                    "interval": interval,
                    "symbol": symbol,
                }
                candles.append(candle)

        return candles

    def interpolate(self, symbol: str, timestamps: List[float], method: str = "linear") -> List[Dict[str, Any]]:
        """Stub: interpolate values at given timestamps."""
        # Placeholder — real implementation would do linear/spline interpolation
        rows = list(self.store.read(symbol))
        if not rows:
            return []
        # Return nearest neighbor stub
        result: List[Dict[str, Any]] = []
        for ts in timestamps:
            nearest = min(rows, key=lambda r: abs(Chunk._extract_time(r) - ts))
            result.append({"timestamp": ts, "value": nearest.get("price", nearest.get("close", 0))})
        return result

    def __repr__(self) -> str:
        return f"TimeSeriesEngine(symbols={len(self.caches)}, store={self.store})"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. S3 STORAGE STUB — Simulasi S3-compatible storage di filesystem lokal
# ═══════════════════════════════════════════════════════════════════════════════

class S3StorageStub:
    """S3-compatible storage stub — simulasi S3 di filesystem lokal."""

    def __init__(self, base_path: str = ".arctic_s3_stub") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.buckets: Set[str] = set()
        self.stats: Dict[str, int] = {"uploads": 0, "downloads": 0, "deletes": 0}

    def create_bucket(self, bucket: str) -> None:
        bucket_path = self.base_path / bucket
        bucket_path.mkdir(parents=True, exist_ok=True)
        self.buckets.add(bucket)

    def delete_bucket(self, bucket: str) -> None:
        bucket_path = self.base_path / bucket
        if bucket_path.exists():
            for f in bucket_path.iterdir():
                f.unlink()
            bucket_path.rmdir()
        self.buckets.discard(bucket)

    def upload_chunk(self, bucket: str, key: str, chunk: Chunk) -> str:
        """Upload chunk ke S3 stub."""
        self.create_bucket(bucket)
        path = self.base_path / bucket / key
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunk": chunk.to_dict(),
            "rows": chunk.data,
        }
        with open(path, "w") as f:
            json.dump(payload, f, default=str, indent=2)
        self.stats["uploads"] += 1
        return str(path)

    def download_chunk(self, bucket: str, key: str) -> Optional[Chunk]:
        """Download chunk dari S3 stub."""
        path = self.base_path / bucket / key
        if not path.exists():
            return None
        with open(path, "r") as f:
            payload = json.load(f)
        self.stats["downloads"] += 1
        chunk_data = payload.get("chunk", {})
        return Chunk(
            data=payload.get("rows", []),
            symbol=chunk_data.get("symbol", ""),
            start_time=chunk_data.get("start_time", 0),
            end_time=chunk_data.get("end_time", 0),
            metadata=chunk_data.get("metadata", {}),
            version=chunk_data.get("version", 1),
            chunk_id=chunk_data.get("chunk_id", ""),
        )

    def list_keys(self, bucket: str, prefix: str = "") -> List[str]:
        bucket_path = self.base_path / bucket
        if not bucket_path.exists():
            return []
        keys = []
        for f in bucket_path.rglob("*.json"):
            rel = f.relative_to(bucket_path).as_posix()
            if not prefix or rel.startswith(prefix):
                keys.append(rel)
        return keys

    def delete_key(self, bucket: str, key: str) -> bool:
        path = self.base_path / bucket / key
        if path.exists():
            path.unlink()
            self.stats["deletes"] += 1
            return True
        return False

    def sync_symbol(self, bucket: str, symbol: str, chunks: List[Chunk]) -> List[str]:
        """Sync semua chunks untuk symbol ke S3."""
        keys: List[str] = []
        for chunk in chunks:
            key = f"{symbol}/{chunk.chunk_id}.json"
            self.upload_chunk(bucket, key, chunk)
            keys.append(key)
        return keys

    def load_symbol(self, bucket: str, symbol: str) -> List[Chunk]:
        """Load semua chunks untuk symbol dari S3."""
        prefix = f"{symbol}/"
        keys = self.list_keys(bucket, prefix)
        chunks: List[Chunk] = []
        for key in keys:
            chunk = self.download_chunk(bucket, key)
            if chunk:
                chunks.append(chunk)
        return chunks

    def __repr__(self) -> str:
        return f"S3StorageStub(buckets={len(self.buckets)}, base={self.base_path})"


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 1 SELESAI — Lanjut ke Bagian 2
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Quick sanity check
    store = ChunkStore()
    registry = SymbolRegistry()
    ts_engine = TimeSeriesEngine(store, registry)
    s3 = S3StorageStub()

    # Generate 100 ticks
    now = time.time()
    ticks = [
        {"timestamp": now + i, "price": 100 + i * 0.1, "volume": 10 + i % 5}
        for i in range(100)
    ]

    chunks = ts_engine.store_ticks("AAPL", ticks)
    print(f"Stored {len(ticks)} ticks in {len(chunks)} chunks")
    print(f"Symbol stats: {store.symbol_stats('AAPL')}")

    # Query range
    results = ts_engine.query_range("AAPL", now, now + 50)
    print(f"Range query returned {len(results)} rows")

    # Resample
    candles = ts_engine.resample("AAPL", "1min")
    print(f"Resampled to {len(candles)} candles")

    # S3 sync
    s3.create_bucket("market-data")
    keys = s3.sync_symbol("market-data", "AAPL", chunks)
    print(f"Synced {len(keys)} chunks to S3 stub")

    loaded = s3.load_symbol("market-data", "AAPL")
    print(f"Loaded {len(loaded)} chunks from S3 stub")
    print("Bagian 1 OK — ArcticDB Native core running.")


# ===== BAGIAN 2: Lanjutan dari Bagian 1 =====

"""
MAGNATRIX-OS Layer 5 — ArcticDB Native (Bagian 2)
Time-Series Storage Engine berbasis pattern ArcticDB (man-group/ArcticDB)
Pure Python, standard library + asyncio, zero external dependencies.

Bagian 2: PandasLikeInterface, VersionEngine, QueryOptimizer,
          CompressionEngine, SchemaEngine, ArcticKernelBridge, ArcticDB + demo
"""

import asyncio
import json
import math
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

# Import dari Bagian 1
from arcticdb_native_part1 import (
    Chunk, ChunkStore, SymbolRegistry, SymbolInfo,
    TimeSeriesEngine, S3StorageStub,
)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. PANDAS-LIKE INTERFACE — API familiar bagi data scientist
# ═══════════════════════════════════════════════════════════════════════════════

class PandasLikeInterface:
    """pandas-style API untuk ArcticDB — read(), write(), head(), tail(), describe(), info()."""

    def __init__(self, ts_engine: TimeSeriesEngine, symbol_registry: SymbolRegistry) -> None:
        self.ts = ts_engine
        self.registry = symbol_registry
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def write(self, symbol: str, data: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> int:
        """Write data — mirip pd.DataFrame.to_arctic()."""
        chunks = self.ts.store_ticks(symbol, data, metadata)
        self._cache[symbol] = list(data)
        return len(data)

    def read(self, symbol: str, start: Optional[float] = None, end: Optional[float] = None,
             columns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Read data — mirip pd.read_arctic()."""
        rows = self.ts.query_range(symbol, start, end)
        if columns:
            rows = [{k: r[k] for k in columns if k in r} for r in rows]
        return rows

    def head(self, symbol: str, n: int = 5) -> List[Dict[str, Any]]:
        """First n rows."""
        all_rows = list(self.ts.store.read(symbol))
        return all_rows[:n]

    def tail(self, symbol: str, n: int = 5) -> List[Dict[str, Any]]:
        """Last n rows."""
        return self.ts.query_latest(symbol, n)

    def describe(self, symbol: str, column: str = "price") -> Dict[str, Any]:
        """Statistik deskriptif untuk kolom numerik."""
        rows = list(self.ts.store.read(symbol))
        values = [r.get(column, 0) for r in rows if column in r]
        if not values:
            return {"error": f"Column '{column}' not found"}

        n = len(values)
        mean = sum(values) / n
        sorted_vals = sorted(values)
        mid = n // 2
        median = (sorted_vals[mid] if n % 2 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2)

        # Variance
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance)

        return {
            "symbol": symbol,
            "column": column,
            "count": n,
            "mean": round(mean, 6),
            "std": round(std, 6),
            "min": round(min(values), 6),
            "25%": round(sorted_vals[n // 4], 6),
            "50%": round(median, 6),
            "75%": round(sorted_vals[3 * n // 4], 6),
            "max": round(max(values), 6),
        }

    def info(self, symbol: str) -> Dict[str, Any]:
        """Info struktur data — mirip DataFrame.info()."""
        stats = self.ts.store.symbol_stats(symbol)
        info = self.registry.get(symbol)
        rows = list(self.ts.store.read(symbol))

        # Infer columns
        columns: Dict[str, str] = {}
        if rows:
            for key in rows[0].keys():
                sample = rows[0].get(key)
                if isinstance(sample, (int, float)):
                    columns[key] = "numeric"
                elif isinstance(sample, str):
                    columns[key] = "string"
                else:
                    columns[key] = type(sample).__name__

        return {
            "symbol": symbol,
            "rows": stats.get("total_rows", 0),
            "chunks": stats.get("chunks", 0),
            "bytes": stats.get("total_bytes", 0),
            "columns": columns,
            "versions": info.versions if info else [],
            "current_version": info.current_version if info else 0,
        }

    def __repr__(self) -> str:
        return f"PandasLikeInterface(symbols={len(self._cache)})"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. VERSION ENGINE — Version control per symbol
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class VersionSnapshot:
    """Snapshot dari sebuah version."""
    version: int
    timestamp: float
    chunks: List[str]  # chunk_ids
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "chunks": self.chunks,
            "metadata": self.metadata,
        }


class VersionEngine:
    """Version control per symbol — rollback, diff, branch stub."""

    def __init__(self, symbol_registry: SymbolRegistry, chunk_store: ChunkStore) -> None:
        self.registry = symbol_registry
        self.store = chunk_store
        # symbol -> version -> snapshot
        self.snapshots: Dict[str, Dict[int, VersionSnapshot]] = {}
        self.branches: Dict[str, Dict[str, int]] = {}  # symbol -> branch -> version

    def snapshot(self, symbol: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Create snapshot dari current state."""
        version = self.registry.bump_version(symbol)
        chunks = self.store.get_chunks(symbol)
        snapshot = VersionSnapshot(
            version=version,
            timestamp=time.time(),
            chunks=[c.chunk_id for c in chunks],
            metadata=metadata or {},
        )
        self.snapshots.setdefault(symbol, {})[version] = snapshot
        return version

    def rollback(self, symbol: str, version: int) -> bool:
        """Rollback ke version tertentu."""
        snap = self.snapshots.get(symbol, {}).get(version)
        if not snap:
            return False
        # In real implementation: restore chunks from backup
        # Stub: mark current version
        info = self.registry.get(symbol)
        if info:
            info.current_version = version
            info.last_modified = time.time()
        return True

    def diff(self, symbol: str, v1: int, v2: int) -> Dict[str, Any]:
        """Diff dua version — stub."""
        s1 = self.snapshots.get(symbol, {}).get(v1)
        s2 = self.snapshots.get(symbol, {}).get(v2)
        if not s1 or not s2:
            return {"error": "Version not found"}

        chunks1 = set(s1.chunks)
        chunks2 = set(s2.chunks)
        return {
            "added_chunks": list(chunks2 - chunks1),
            "removed_chunks": list(chunks1 - chunks2),
            "common_chunks": list(chunks1 & chunks2),
            "version_from": v1,
            "version_to": v2,
        }

    def list_versions(self, symbol: str) -> List[Dict[str, Any]]:
        """List semua version untuk symbol."""
        snaps = self.snapshots.get(symbol, {})
        return [s.to_dict() for s in sorted(snaps.values(), key=lambda x: x.version)]

    def create_branch(self, symbol: str, branch_name: str, from_version: Optional[int] = None) -> bool:
        """Stub: create branch dari version."""
        info = self.registry.get(symbol)
        if not info:
            return False
        version = from_version or info.current_version
        self.branches.setdefault(symbol, {})[branch_name] = version
        return True

    def list_branches(self, symbol: str) -> Dict[str, int]:
        return dict(self.branches.get(symbol, {}))

    def __repr__(self) -> str:
        total_snaps = sum(len(v) for v in self.snapshots.values())
        return f"VersionEngine(snapshots={total_snaps})"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. QUERY OPTIMIZER — Pruning, filtering, predicate pushdown
# ═══════════════════════════════════════════════════════════════════════════════

class QueryOptimizer:
    """Optimize queries — time range pruning, chunk filtering, predicate pushdown."""

    def __init__(self, chunk_store: ChunkStore) -> None:
        self.store = chunk_store
        self.stats: Dict[str, Any] = {"queries_optimized": 0, "chunks_skipped": 0, "rows_filtered": 0}

    def optimize_time_range(self, symbol: str, start: Optional[float], end: Optional[float]) -> List[Chunk]:
        """Prune chunks yang di luar time range."""
        chunks = self.store.get_chunks(symbol)
        filtered: List[Chunk] = []
        for chunk in chunks:
            if start and chunk.end_time < start:
                self.stats["chunks_skipped"] += 1
                continue
            if end and chunk.start_time > end:
                self.stats["chunks_skipped"] += 1
                continue
            filtered.append(chunk)
        return filtered

    def filter_predicate(self, chunks: List[Chunk], predicate: Callable[[Dict[str, Any]], bool]) -> Iterator[Dict[str, Any]]:
        """Predicate pushdown — filter rows dalam chunks."""
        for chunk in chunks:
            for row in chunk.data:
                if predicate(row):
                    yield row
                else:
                    self.stats["rows_filtered"] += 1

    def column_pruning(self, rows: Iterator[Dict[str, Any]], columns: List[str]) -> Iterator[Dict[str, Any]]:
        """Hanya ambil kolom yang diminta."""
        for row in rows:
            yield {k: row[k] for k in columns if k in row}

    def estimate_cost(self, symbol: str, start: Optional[float], end: Optional[float]) -> Dict[str, Any]:
        """Estimasi cost query."""
        all_chunks = self.store.get_chunks(symbol)
        relevant = self.optimize_time_range(symbol, start, end)
        total_rows = sum(c.row_count for c in all_chunks)
        relevant_rows = sum(c.row_count for c in relevant)

        return {
            "symbol": symbol,
            "total_chunks": len(all_chunks),
            "relevant_chunks": len(relevant),
            "total_rows": total_rows,
            "relevant_rows": relevant_rows,
            "skip_ratio": 1 - (relevant_rows / total_rows) if total_rows else 0,
        }

    def __repr__(self) -> str:
        return f"QueryOptimizer(stats={self.stats})"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. COMPRESSION ENGINE — lz4/zstd stub
# ═══════════════════════════════════════════════════════════════════════════════

class CompressionEngine:
    """Compression stub — simulasi lz4/zstd compression."""

    def __init__(self, algorithm: str = "lz4") -> None:
        self.algorithm = algorithm
        self.compression_ratio = 0.3 if algorithm == "lz4" else 0.2  # simulated
        self.stats: Dict[str, int] = {"compressed": 0, "decompressed": 0, "bytes_saved": 0}

    def compress(self, data: str) -> bytes:
        """Stub compression — return encoded dengan marker."""
        raw = data.encode("utf-8")
        # Simulasi: tidak real compression, tapi track
        compressed_size = int(len(raw) * self.compression_ratio)
        self.stats["compressed"] += 1
        self.stats["bytes_saved"] += len(raw) - compressed_size
        # Marker: COMPRESSED:<algo>:<size>:<data>
        marker = f"COMPRESSED:{self.algorithm}:{compressed_size}:".encode()
        return marker + raw[:compressed_size]

    def decompress(self, compressed: bytes) -> str:
        """Stub decompression."""
        self.stats["decompressed"] += 1
        # Extract original from stub (simplified)
        try:
            text = compressed.decode("utf-8", errors="ignore")
            if text.startswith("COMPRESSED:"):
                # Return truncated data (stub limitation)
                parts = text.split(":", 3)
                if len(parts) >= 4:
                    return parts[3]
            return text
        except Exception:
            return compressed.decode("utf-8", errors="ignore")

    def compress_chunk(self, chunk: Chunk) -> bytes:
        """Compress chunk ke bytes."""
        json_str = json.dumps({"rows": chunk.data, "meta": chunk.to_dict()}, default=str)
        return self.compress(json_str)

    def decompress_chunk(self, compressed: bytes) -> Optional[Chunk]:
        """Decompress bytes ke chunk."""
        json_str = self.decompress(compressed)
        try:
            payload = json.loads(json_str)
            meta = payload.get("meta", {})
            return Chunk(
                data=payload.get("rows", []),
                symbol=meta.get("symbol", ""),
                start_time=meta.get("start_time", 0),
                end_time=meta.get("end_time", 0),
                metadata=meta.get("metadata", {}),
                version=meta.get("version", 1),
                chunk_id=meta.get("chunk_id", ""),
            )
        except json.JSONDecodeError:
            return None

    def __repr__(self) -> str:
        return f"CompressionEngine({self.algorithm}, saved={self.stats['bytes_saved']})"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SCHEMA ENGINE — Schema inference, validation, evolution
# ═══════════════════════════════════════════════════════════════════════════════

class SchemaEngine:
    """Schema inference, validation, dan evolution tracking."""

    TYPE_MAP: Dict[type, str] = {
        int: "INTEGER",
        float: "FLOAT",
        str: "STRING",
        bool: "BOOLEAN",
        list: "ARRAY",
        dict: "OBJECT",
    }

    def __init__(self, symbol_registry: SymbolRegistry) -> None:
        self.registry = symbol_registry
        self.schemas: Dict[str, Dict[str, str]] = {}  # symbol -> column -> type
        self.history: Dict[str, List[Dict[str, Any]]] = {}  # evolution history

    def infer(self, rows: List[Dict[str, Any]]) -> Dict[str, str]:
        """Infer schema dari sample rows."""
        if not rows:
            return {}
        schema: Dict[str, str] = {}
        for key in rows[0].keys():
            values = [r.get(key) for r in rows if key in r and r.get(key) is not None]
            if not values:
                schema[key] = "UNKNOWN"
                continue
            sample = values[0]
            py_type = type(sample)
            schema[key] = self.TYPE_MAP.get(py_type, py_type.__name__.upper())
        return schema

    def register_schema(self, symbol: str, rows: List[Dict[str, Any]]) -> Dict[str, str]:
        """Infer dan register schema untuk symbol."""
        schema = self.infer(rows)
        self.schemas[symbol] = schema
        info = self.registry.get(symbol)
        if info:
            info.schema = schema
        self.history.setdefault(symbol, []).append({
            "timestamp": time.time(),
            "schema": dict(schema),
            "action": "registered",
        })
        return schema

    def validate(self, symbol: str, row: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validasi row terhadap schema yang terdaftar."""
        schema = self.schemas.get(symbol, {})
        if not schema:
            return True, []

        errors: List[str] = []
        for col, expected_type in schema.items():
            if col in row:
                value = row[col]
                actual = self.TYPE_MAP.get(type(value), type(value).__name__.upper())
                if actual != expected_type and value is not None:
                    errors.append(f"{col}: expected {expected_type}, got {actual}")
        return len(errors) == 0, errors

    def evolve(self, symbol: str, new_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evolusi schema — tambah kolom baru jika muncul."""
        old_schema = self.schemas.get(symbol, {})
        new_schema = self.infer(new_rows)

        added: List[str] = []
        changed: List[str] = []

        for col, new_type in new_schema.items():
            if col not in old_schema:
                added.append(col)
                old_schema[col] = new_type
            elif old_schema.get(col) != new_type:
                changed.append(f"{col}: {old_schema[col]} -> {new_type}")
                old_schema[col] = new_type

        self.schemas[symbol] = old_schema
        info = self.registry.get(symbol)
        if info:
            info.schema = old_schema

        self.history.setdefault(symbol, []).append({
            "timestamp": time.time(),
            "schema": dict(old_schema),
            "added": added,
            "changed": changed,
            "action": "evolved",
        })

        return {"added": added, "changed": changed, "schema": old_schema}

    def get_history(self, symbol: str) -> List[Dict[str, Any]]:
        return list(self.history.get(symbol, []))

    def __repr__(self) -> str:
        return f"SchemaEngine(schemas={len(self.schemas)})"


# ═══════════════════════════════════════════════════════════════════════════════
# 11. ARCTIC KERNEL BRIDGE — Bridge ke event_bus & service_registry
# ═══════════════════════════════════════════════════════════════════════════════

class ArcticKernelBridge:
    """Bridge ArcticDB ke MAGNATRIX kernel (event_bus & service_registry patterns)."""

    def __init__(self, arcticdb: "ArcticDB") -> None:
        self.arctic = arcticdb
        self.events: List[Dict[str, Any]] = []
        self.handlers: Dict[str, List[Callable]] = {}
        self.services: Dict[str, Any] = {}  # service registry stub

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish event ke kernel."""
        event = {
            "id": f"evt_{uuid.uuid4().hex[:8]}",
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        }
        self.events.append(event)
        for handler in self.handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                print(f"Handler error: {e}")

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        self.handlers.setdefault(event_type, []).append(handler)

    def register_service(self, name: str, instance: Any) -> None:
        """Register service ke registry."""
        self.services[name] = {
            "instance": instance,
            "registered_at": time.time(),
            "status": "active",
        }
        self.publish("service_registered", {"name": name, "type": type(instance).__name__})

    def get_service(self, name: str) -> Optional[Any]:
        svc = self.services.get(name)
        return svc["instance"] if svc else None

    def notify_store(self, symbol: str, rows: int, version: int) -> None:
        """Notify kernel bahwa data telah di-store."""
        self.publish("data_stored", {
            "symbol": symbol,
            "rows": rows,
            "version": version,
            "timestamp": time.time(),
        })

    def notify_query(self, symbol: str, rows: int, duration_ms: float) -> None:
        """Notify kernel bahwa query selesai."""
        self.publish("query_complete", {
            "symbol": symbol,
            "rows": rows,
            "duration_ms": duration_ms,
        })

    def __repr__(self) -> str:
        return f"ArcticKernelBridge(events={len(self.events)}, services={len(self.services)})"


# ═══════════════════════════════════════════════════════════════════════════════
# 12. ARCTICDB — Main Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class ArcticDB:
    """Main orchestrator — compose semua komponen ArcticDB Native."""

    def __init__(self, base_path: str = ".arcticdb_native") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Core components
        self.chunk_store = ChunkStore()
        self.symbol_registry = SymbolRegistry()
        self.ts_engine = TimeSeriesEngine(self.chunk_store, self.symbol_registry)
        self.s3_stub = S3StorageStub(str(self.base_path / "s3"))

        # Advanced components
        self.pandas = PandasLikeInterface(self.ts_engine, self.symbol_registry)
        self.version_engine = VersionEngine(self.symbol_registry, self.chunk_store)
        self.query_optimizer = QueryOptimizer(self.chunk_store)
        self.compression = CompressionEngine("lz4")
        self.schema_engine = SchemaEngine(self.symbol_registry)

        # Kernel bridge
        self.kernel = ArcticKernelBridge(self)

        # Stats
        self.stats: Dict[str, Any] = {
            "started_at": time.time(),
            "stores": 0,
            "queries": 0,
            "snapshots": 0,
        }

    def store(self, symbol: str, data: List[Dict[str, Any]],
              metadata: Optional[Dict[str, Any]] = None) -> int:
        """Store data — infer schema, write chunks, notify kernel."""
        t0 = time.time()

        # Register symbol
        self.symbol_registry.register(symbol, metadata=metadata)

        # Infer schema
        if data:
            self.schema_engine.register_schema(symbol, data)

        # Store data
        chunks = self.ts_engine.store_ticks(symbol, data, metadata)

        # Snapshot version
        version = self.version_engine.snapshot(symbol, metadata={"rows": len(data)})

        # Notify kernel
        self.kernel.notify_store(symbol, len(data), version)

        self.stats["stores"] += 1
        return len(data)

    def query(self, symbol: str, start: Optional[float] = None,
              end: Optional[float] = None, columns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Query dengan optimization."""
        t0 = time.time()

        # Optimize: prune chunks
        chunks = self.query_optimizer.optimize_time_range(symbol, start, end)

        # Read rows
        rows = list(self.ts_engine.query_range(symbol, start, end))

        # Column pruning
        if columns:
            rows = [{k: r[k] for k in columns if k in r} for r in rows]

        duration = (time.time() - t0) * 1000
        self.kernel.notify_query(symbol, len(rows), duration)
        self.stats["queries"] += 1

        return rows

    def resample(self, symbol: str, interval: str) -> List[Dict[str, Any]]:
        """Resample ke interval."""
        return self.ts_engine.resample(symbol, interval)

    def snapshot(self, symbol: str) -> int:
        """Create version snapshot."""
        v = self.version_engine.snapshot(symbol)
        self.stats["snapshots"] += 1
        return v

    def rollback(self, symbol: str, version: int) -> bool:
        return self.version_engine.rollback(symbol, version)

    def versions(self, symbol: str) -> List[Dict[str, Any]]:
        return self.version_engine.list_versions(symbol)

    def describe(self, symbol: str, column: str = "price") -> Dict[str, Any]:
        return self.pandas.describe(symbol, column)

    def info(self, symbol: str) -> Dict[str, Any]:
        return self.pandas.info(symbol)

    def sync_to_s3(self, bucket: str, symbol: str) -> List[str]:
        """Sync symbol chunks ke S3 stub."""
        chunks = self.chunk_store.get_chunks(symbol)
        return self.s3_stub.sync_symbol(bucket, symbol, chunks)

    def load_from_s3(self, bucket: str, symbol: str) -> int:
        """Load symbol chunks dari S3 stub."""
        chunks = self.s3_stub.load_symbol(bucket, symbol)
        for chunk in chunks:
            if symbol not in self.chunk_store.chunks:
                self.chunk_store.chunks[symbol] = []
            self.chunk_store.chunks[symbol].append(chunk)
        return len(chunks)

    def compact(self, symbol: str) -> int:
        return self.chunk_store.compact(symbol)

    def list_symbols(self) -> List[str]:
        return self.symbol_registry.list_all()

    def stats_summary(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "symbols": len(self.symbol_registry.list_all()),
            "total_chunks": sum(len(c) for c in self.chunk_store.chunks.values()),
            "kernel_events": len(self.kernel.events),
        }

    def __repr__(self) -> str:
        return f"ArcticDB(symbols={len(self.list_symbols())}, stores={self.stats['stores']})"


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("ARCTICDB NATIVE — MAGNATRIX-OS Layer 5 Demo")
    print("=" * 70)

    db = ArcticDB(base_path=".demo_arcticdb")

    # Create 3 symbols
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
    now = time.time()

    for sym in symbols:
        print(f"\n--- Symbol: {sym} ---")

        # Generate 1000 ticks
        ticks = []
        base_price = 50000 if "BTC" in sym else (3000 if "ETH" in sym else 150)
        for i in range(1000):
            tick = {
                "timestamp": now + i,
                "price": base_price + (i % 100) * 0.5 + (i % 7) * 2,
                "volume": 100 + (i % 50) * 10,
                "bid": base_price + (i % 100) * 0.5 - 0.25,
                "ask": base_price + (i % 100) * 0.5 + 0.25,
            }
            ticks.append(tick)

        # Store
        stored = db.store(sym, ticks, metadata={"exchange": "demo", "asset": sym})
        print(f"Stored {stored} ticks")

        # Query time range (first 100 seconds)
        results = db.query(sym, start=now, end=now + 100)
        print(f"Range query [0-100s]: {len(results)} rows")

        # Resample to 1min
        candles = db.resample(sym, "1min")
        print(f"Resampled to 1min: {len(candles)} candles")
        if candles:
            print(f"  First candle: {candles[0]}")

        # Show version history
        db.snapshot(sym)
        db.snapshot(sym)
        versions = db.versions(sym)
        print(f"Version history: {len(versions)} versions")
        for v in versions:
            print(f"  v{v['version']} at {datetime.fromtimestamp(v['timestamp']).strftime('%H:%M:%S')}")

        # Rollback demo
        if len(versions) >= 2:
            rolled = db.rollback(sym, versions[0]["version"])
            print(f"Rollback to v{versions[0]['version']}: {'OK' if rolled else 'FAIL'}")

        # Describe
        desc = db.describe(sym, "price")
        print(f"Describe 'price': count={desc['count']}, mean={desc['mean']}, std={desc['std']}")

        # Info
        info = db.info(sym)
        print(f"Info: rows={info['rows']}, chunks={info['chunks']}, cols={list(info['columns'].keys())}")

    # S3 sync demo
    print("\n--- S3 Sync ---")
    for sym in symbols:
        keys = db.sync_to_s3("market-data", sym)
        print(f"{sym}: synced {len(keys)} chunks to S3")

    # Stats
    print("\n--- Final Stats ---")
    stats = db.stats_summary()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Kernel events
    print(f"\n--- Kernel Events (last 5) ---")
    for evt in db.kernel.events[-5:]:
        print(f"  {evt['type']}: {evt['payload']}")

    print("\n" + "=" * 70)
    print("Demo selesai. ArcticDB Native siap untuk MAGNATRIX-OS.")
    print("=" * 70)
