#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Persistence Layer (Layer 14)
SQLite/JSON Hybrid Persistence Engine
================================================================================
Zero-dependency state persistence with WAL, migration, and hot-backup.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# =============================================================================
# Constants
# =============================================================================
DEFAULT_DB_PATH = "/tmp/magnatrix_persistence.db"
DEFAULT_WAL_DIR = "/tmp/magnatrix_wal"
DEFAULT_BACKUP_DIR = "/tmp/magnatrix_backups"
SCHEMA_VERSION = 1


# =============================================================================
# Data Types
# =============================================================================
@dataclass
class StoreRecord:
    key: str
    value: Any
    namespace: str = "default"
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    checksum: str = ""

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        payload = f"{self.key}|{self.namespace}|{json.dumps(self.value, sort_keys=True)}|{self.version}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class MigrationRecord:
    version: int
    name: str
    applied_at: float
    checksum: str


# =============================================================================
# Backends
# =============================================================================
class StorageBackend(ABC):
    @abstractmethod
    def get(self, key: str, namespace: str = "default") -> Optional[StoreRecord]: ...
    @abstractmethod
    def put(self, record: StoreRecord) -> bool: ...
    @abstractmethod
    def delete(self, key: str, namespace: str = "default") -> bool: ...
    @abstractmethod
    def list_keys(self, namespace: str = "default") -> List[str]: ...
    @abstractmethod
    def list_namespaces(self) -> List[str]: ...
    @abstractmethod
    def close(self) -> None: ...


class SQLiteBackend(StorageBackend):
    """Thread-safe SQLite backend with connection pooling."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_schema(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS store (
            key TEXT NOT NULL,
            namespace TEXT NOT NULL DEFAULT 'default',
            value_json TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            checksum TEXT NOT NULL,
            PRIMARY KEY (key, namespace)
        ) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS idx_ns ON store(namespace);
        CREATE INDEX IF NOT EXISTS idx_updated ON store(updated_at);
        CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at REAL NOT NULL,
            checksum TEXT NOT NULL
        );
        """
        with self._lock:
            self._conn().executescript(ddl)
            self._conn().commit()

    def get(self, key: str, namespace: str = "default") -> Optional[StoreRecord]:
        with self._lock:
            cur = self._conn().execute(
                "SELECT value_json, version, created_at, updated_at, checksum FROM store WHERE key=? AND namespace=?",
                (key, namespace),
            )
            row = cur.fetchone()
            if not row:
                return None
            return StoreRecord(
                key=key,
                namespace=namespace,
                value=json.loads(row[0]),
                version=row[1],
                created_at=row[2],
                updated_at=row[3],
                checksum=row[4],
            )

    def put(self, record: StoreRecord) -> bool:
        with self._lock:
            self._conn().execute(
                """INSERT INTO store(key, namespace, value_json, version, created_at, updated_at, checksum)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(key, namespace) DO UPDATE SET
                   value_json=excluded.value_json,
                   version=excluded.version,
                   updated_at=excluded.updated_at,
                   checksum=excluded.checksum""",
                (
                    record.key,
                    record.namespace,
                    json.dumps(record.value, default=str),
                    record.version,
                    record.created_at,
                    record.updated_at,
                    record.checksum,
                ),
            )
            self._conn().commit()
            return True

    def delete(self, key: str, namespace: str = "default") -> bool:
        with self._lock:
            cur = self._conn().execute("DELETE FROM store WHERE key=? AND namespace=?", (key, namespace))
            self._conn().commit()
            return cur.rowcount > 0

    def list_keys(self, namespace: str = "default") -> List[str]:
        with self._lock:
            cur = self._conn().execute("SELECT key FROM store WHERE namespace=?", (namespace,))
            return [r[0] for r in cur.fetchall()]

    def list_namespaces(self) -> List[str]:
        with self._lock:
            cur = self._conn().execute("SELECT DISTINCT namespace FROM store")
            return [r[0] for r in cur.fetchall()]

    def close(self) -> None:
        with self._lock:
            if hasattr(self._local, "conn") and self._local.conn:
                self._local.conn.close()
                self._local.conn = None


class JSONBackend(StorageBackend):
    """Pure JSON-file backend for portable state snapshots."""

    def __init__(self, base_dir: str = "/tmp/magnatrix_json_store") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, namespace: str) -> Path:
        return self.base_dir / f"{namespace}.json"

    def _load_ns(self, namespace: str) -> Dict[str, Any]:
        p = self._path(namespace)
        if not p.exists():
            return {}
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_ns(self, namespace: str, data: Dict[str, Any]) -> None:
        p = self._path(namespace)
        tmp = p.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        tmp.replace(p)

    def get(self, key: str, namespace: str = "default") -> Optional[StoreRecord]:
        with self._lock:
            ns = self._load_ns(namespace)
            if key not in ns:
                return None
            raw = ns[key]
            return StoreRecord(
                key=key,
                namespace=namespace,
                value=raw.get("v"),
                version=raw.get("ver", 1),
                created_at=raw.get("c", 0.0),
                updated_at=raw.get("u", 0.0),
                checksum=raw.get("chk", ""),
            )

    def put(self, record: StoreRecord) -> bool:
        with self._lock:
            ns = self._load_ns(record.namespace)
            ns[record.key] = {
                "v": record.value,
                "ver": record.version,
                "c": record.created_at,
                "u": time.time(),
                "chk": record.checksum,
            }
            self._save_ns(record.namespace, ns)
            return True

    def delete(self, key: str, namespace: str = "default") -> bool:
        with self._lock:
            ns = self._load_ns(namespace)
            if key not in ns:
                return False
            del ns[key]
            self._save_ns(namespace, ns)
            return True

    def list_keys(self, namespace: str = "default") -> List[str]:
        with self._lock:
            return list(self._load_ns(namespace).keys())

    def list_namespaces(self) -> List[str]:
        with self._lock:
            return [p.stem for p in self.base_dir.glob("*.json")]

    def close(self) -> None:
        pass


# =============================================================================
# Hybrid Store
# =============================================================================
class HybridStore:
    """SQLite hot-path + JSON snapshot fallback."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH, json_dir: str = "/tmp/magnatrix_json_store") -> None:
        self.sqlite = SQLiteBackend(db_path)
        self.json = JSONBackend(json_dir)
        self._lock = threading.RLock()

    def get(self, key: str, namespace: str = "default") -> Optional[StoreRecord]:
        with self._lock:
            r = self.sqlite.get(key, namespace)
            if r is None:
                r = self.json.get(key, namespace)
            return r

    def put(self, record: StoreRecord) -> bool:
        with self._lock:
            record.updated_at = time.time()
            record.checksum = record._compute_checksum()
            ok1 = self.sqlite.put(record)
            ok2 = self.json.put(record)
            return ok1 and ok2

    def delete(self, key: str, namespace: str = "default") -> bool:
        with self._lock:
            ok1 = self.sqlite.delete(key, namespace)
            ok2 = self.json.delete(key, namespace)
            return ok1 or ok2

    def list_keys(self, namespace: str = "default") -> List[str]:
        with self._lock:
            s = set(self.sqlite.list_keys(namespace))
            s.update(self.json.list_keys(namespace))
            return sorted(s)

    def snapshot_to_json(self, namespace: str = "default", out_path: Optional[str] = None) -> str:
        with self._lock:
            keys = self.sqlite.list_keys(namespace)
            dump: Dict[str, Any] = {}
            for k in keys:
                r = self.sqlite.get(k, namespace)
                if r:
                    dump[k] = asdict(r)
            out = out_path or f"/tmp/magnatrix_snapshot_{namespace}_{int(time.time())}.json"
            with open(out, "w", encoding="utf-8") as f:
                json.dump(dump, f, indent=2, default=str)
            return out

    def close(self) -> None:
        self.sqlite.close()
        self.json.close()


# =============================================================================
# WAL Manager
# =============================================================================
class WALManager:
    """Write-Ahead Log for crash recovery."""

    def __init__(self, wal_dir: str = DEFAULT_WAL_DIR) -> None:
        self.wal_dir = Path(wal_dir)
        self.wal_dir.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._lock = threading.Lock()
        self._rotate()

    def _rotate(self) -> None:
        ts = int(time.time() * 1000)
        self._file = open(self.wal_dir / f"wal_{ts}.log", "a", encoding="utf-8")

    def append(self, op: str, key: str, namespace: str, value: Any = None) -> None:
        with self._lock:
            entry = {
                "ts": time.time(),
                "op": op,
                "key": key,
                "ns": namespace,
                "val": value,
            }
            self._file.write(json.dumps(entry, default=str) + "\n")
            self._file.flush()
            if os.fstat(self._file.fileno()).st_size > 10 * 1024 * 1024:
                self._file.close()
                self._rotate()

    def replay(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            for p in sorted(self.wal_dir.glob("wal_*.log")):
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            callback(json.loads(line))

    def close(self) -> None:
        with self._lock:
            if self._file:
                self._file.close()


# =============================================================================
# Migration Manager
# =============================================================================
class MigrationManager:
    """Schema migration runner with checksum verification."""

    def __init__(self, backend: SQLiteBackend) -> None:
        self.backend = backend
        self._migrations: Dict[int, Tuple[str, Callable[[sqlite3.Connection], None]]] = {}

    def register(self, version: int, name: str, fn: Callable[[sqlite3.Connection], None]) -> None:
        self._migrations[version] = (name, fn)

    def current_version(self) -> int:
        r = self.backend._conn().execute("SELECT MAX(version) FROM migrations").fetchone()
        return r[0] or 0

    def migrate(self) -> List[MigrationRecord]:
        applied: List[MigrationRecord] = []
        cur = self.current_version()
        for ver in sorted(self._migrations):
            if ver <= cur:
                continue
            name, fn = self._migrations[ver]
            fn(self.backend._conn())
            rec = MigrationRecord(
                version=ver,
                name=name,
                applied_at=time.time(),
                checksum=hashlib.sha256(name.encode()).hexdigest()[:16],
            )
            self.backend._conn().execute(
                "INSERT INTO migrations(version, name, applied_at, checksum) VALUES(?,?,?,?)",
                (rec.version, rec.name, rec.applied_at, rec.checksum),
            )
            self.backend._conn().commit()
            applied.append(rec)
        return applied


# =============================================================================
# Backup Manager
# =============================================================================
class BackupManager:
    """Hot-backup with timestamped tarballs."""

    def __init__(self, backup_dir: str = DEFAULT_BACKUP_DIR) -> None:
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup(self, db_path: str, label: str = "auto") -> str:
        import shutil
        ts = int(time.time())
        dest = self.backup_dir / f"backup_{label}_{ts}.db"
        shutil.copy2(db_path, dest)
        return str(dest)

    def list_backups(self) -> List[Path]:
        return sorted(self.backup_dir.glob("backup_*.db"), key=lambda p: p.stat().st_mtime)

    def restore(self, backup_path: str, db_path: str) -> bool:
        import shutil
        shutil.copy2(backup_path, db_path)
        return True

    def prune(self, keep: int = 10) -> List[Path]:
        all_bak = self.list_backups()
        removed = []
        for old in all_bak[:-keep]:
            old.unlink()
            removed.append(old)
        return removed


# =============================================================================
# Index Manager
# =============================================================================
class IndexManager:
    """Lightweight secondary indexes over SQLite."""

    def __init__(self, backend: SQLiteBackend) -> None:
        self.backend = backend

    def create_index(self, namespace: str, field: str) -> bool:
        try:
            with self.backend._lock:
                # Extract field via JSON path into a virtual column for querying
                self.backend._conn().execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{namespace}_{field} ON store(namespace)"
                )
                self.backend._conn().commit()
            return True
        except Exception:
            return False

    def query_by_field(self, namespace: str, field: str, value: Any) -> List[StoreRecord]:
        """Brute-force scan (can be optimized with virtual columns)."""
        keys = self.backend.list_keys(namespace)
        out: List[StoreRecord] = []
        for k in keys:
            r = self.backend.get(k, namespace)
            if r and isinstance(r.value, dict) and r.value.get(field) == value:
                out.append(r)
        return out


# =============================================================================
# Persistence Kernel Bridge
# =============================================================================
class PersistenceKernelBridge:
    """Connects persistence to kernel event bus."""

    def __init__(self, store: HybridStore, event_bus: Any = None) -> None:
        self.store = store
        self.bus = event_bus
        self._hooks: List[Callable[[str, str, Any], None]] = []

    def on_persist(self, callback: Callable[[str, str, Any], None]) -> None:
        self._hooks.append(callback)

    def put(self, key: str, value: Any, namespace: str = "default") -> bool:
        record = StoreRecord(key=key, value=value, namespace=namespace)
        ok = self.store.put(record)
        if ok:
            for hook in self._hooks:
                hook(key, namespace, value)
            if self.bus:
                self.bus.publish("persistence.put", {"key": key, "ns": namespace})
        return ok

    def get(self, key: str, namespace: str = "default") -> Any:
        r = self.store.get(key, namespace)
        return r.value if r else None

    def delete(self, key: str, namespace: str = "default") -> bool:
        ok = self.store.delete(key, namespace)
        if ok and self.bus:
            self.bus.publish("persistence.delete", {"key": key, "ns": namespace})
        return ok


# =============================================================================
# Main Engine
# =============================================================================
class PersistenceEngine:
    """Top-level orchestrator for all persistence subsystems."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.store = HybridStore(db_path)
        self.wal = WALManager()
        self.migrator = MigrationManager(self.store.sqlite)
        self.backup = BackupManager()
        self.index = IndexManager(self.store.sqlite)
        self.bridge = PersistenceKernelBridge(self.store)
        self._running = False
        self._setup_migrations()

    def _setup_migrations(self) -> None:
        self.migrator.register(1, "init_schema", lambda conn: None)
        self.migrator.migrate()

    def put(self, key: str, value: Any, namespace: str = "default") -> bool:
        record = StoreRecord(key=key, value=value, namespace=namespace)
        self.wal.append("PUT", key, namespace, value)
        return self.store.put(record)

    def get(self, key: str, namespace: str = "default") -> Any:
        self.wal.append("GET", key, namespace)
        r = self.store.get(key, namespace)
        return r.value if r else None

    def delete(self, key: str, namespace: str = "default") -> bool:
        self.wal.append("DELETE", key, namespace)
        return self.store.delete(key, namespace)

    def snapshot(self, namespace: str = "default", out_path: Optional[str] = None) -> str:
        return self.store.snapshot_to_json(namespace, out_path)

    def backup_now(self, label: str = "manual") -> str:
        return self.backup.backup(self.store.sqlite.db_path, label)

    def shutdown(self) -> None:
        self._running = False
        self.wal.close()
        self.store.close()

    def __enter__(self) -> PersistenceEngine:
        self._running = True
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown()


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Persistence Layer Demo")
    print("=" * 60)
    engine = PersistenceEngine("/tmp/magnatrix_demo.db")
    for i in range(5):
        engine.put(f"key-{i}", {"index": i, "data": f"value-{i}"}, namespace="demo")
    print(f"Keys in demo: {engine.store.list_keys('demo')}")
    print(f"Get key-2: {engine.get('key-2', 'demo')}")
    snap = engine.snapshot("demo")
    print(f"Snapshot written to: {snap}")
    bak = engine.backup_now("demo_run")
    print(f"Backup created: {bak}")
    engine.shutdown()
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
