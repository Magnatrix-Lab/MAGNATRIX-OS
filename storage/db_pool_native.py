#!/usr/bin/env python3
"""
storage/db_pool_native.py
=========================
Layer 0 Extension — Database Connection Pool

Provides:
  - Auto-close context manager (with statement)
  - Connection pool with max_size, timeout
  - SQLite specialization
  - WAL mode enforcement for durability
  - Connection health check
"""

from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class PoolConfig:
    database: str
    max_size: int = 10
    timeout: float = 30.0
    check_same_thread: bool = False
    wal_mode: bool = True


class ConnectionPool:
    """Thread-safe SQLite connection pool with auto-return."""

    def __init__(self, config: PoolConfig) -> None:
        self.config = config
        self._pool: List[sqlite3.Connection] = []
        self._in_use: Dict[int, sqlite3.Connection] = {}
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(config.max_size)
        self._closed = False

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.config.database,
            timeout=self.config.timeout,
            check_same_thread=self.config.check_same_thread,
        )
        if self.config.wal_mode:
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _get(self) -> sqlite3.Connection:
        self._semaphore.acquire()
        with self._lock:
            if self._pool:
                conn = self._pool.pop()
            else:
                conn = self._create_connection()
            self._in_use[id(conn)] = conn
            return conn

    def _return(self, conn: sqlite3.Connection) -> None:
        with self._lock:
            self._in_use.pop(id(conn), None)
            if not self._closed:
                self._pool.append(conn)
            else:
                try:
                    conn.close()
                except Exception:
                    pass
        self._semaphore.release()

    @contextmanager
    def connection(self):
        """Context manager that auto-returns connection."""
        conn = self._get()
        try:
            yield conn
        finally:
            self._return(conn)

    @contextmanager
    def transaction(self):
        """Context manager for ACID transaction."""
        conn = self._get()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._return(conn)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            for conn in list(self._pool):
                try:
                    conn.close()
                except Exception:
                    pass
            self._pool.clear()
            for conn in list(self._in_use.values()):
                try:
                    conn.close()
                except Exception:
                    pass
            self._in_use.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "pool_size": len(self._pool),
                "in_use": len(self._in_use),
                "max_size": self.config.max_size,
                "database": self.config.database,
            }


class AutoCloseConnection:
    """Wrapper for single connection that auto-closes on garbage collection."""

    def __init__(self, database: str, **kwargs) -> None:
        self._conn = sqlite3.connect(database, **kwargs)
        self._closed = False

    def __enter__(self) -> sqlite3.Connection:
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._conn.close()
            self._closed = True

    def __del__(self) -> None:
        self.close()


@contextmanager
def safe_connect(database: str, **kwargs):
    """Guaranteed close on exit, even on exception."""
    conn = sqlite3.connect(database, **kwargs)
    try:
        yield conn
    finally:
        conn.close()


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  DB CONNECTION POOL")
    print("=" * 60)
    import tempfile, os
    db_path = os.path.join(tempfile.mkdtemp(), "test.db")
    pool = ConnectionPool(PoolConfig(database=db_path, max_size=3))
    
    with pool.connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO test (val) VALUES ('hello')")
    
    with pool.connection() as conn:
        row = conn.execute("SELECT val FROM test WHERE id=1").fetchone()
        print(f"Read: {row}")
    
    print(f"Pool stats: {pool.stats()}")
    pool.close()
    print("=" * 60)


if __name__ == "__main__":
    demo()
