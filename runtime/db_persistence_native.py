"""runtime/db_persistence_native.py — Database persistence layer"""
from __future__ import annotations
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

class DBPersistence:
    """SQLite-based persistence layer with connection pooling."""

    def __init__(self, db_path: str = "magnatrix.db"):
        self.db_path = db_path
        self._pool: List[sqlite3.Connection] = []
        self._max_pool = 5
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                type TEXT,
                data TEXT,
                created REAL,
                updated REAL
            )
        """)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        with self._lock:
            if self._pool:
                return self._pool.pop()
        return sqlite3.connect(self.db_path)

    def _return_conn(self, conn: sqlite3.Connection) -> None:
        with self._lock:
            if len(self._pool) < self._max_pool:
                self._pool.append(conn)
            else:
                conn.close()

    def create(self, entity_id: str, entity_type: str, data: Dict[str, Any]) -> bool:
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO entities (id, type, data, created, updated) VALUES (?, ?, ?, ?, ?)",
                (entity_id, entity_type, str(data), time.time(), time.time())
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            self._return_conn(conn)

    def read(self, entity_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "type": row[1], "data": row[2], "created": row[3], "updated": row[4]}
            return None
        finally:
            self._return_conn(conn)

    def update(self, entity_id: str, data: Dict[str, Any]) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "UPDATE entities SET data = ?, updated = ? WHERE id = ?",
                (str(data), time.time(), entity_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            self._return_conn(conn)

    def delete(self, entity_id: str) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            self._return_conn(conn)

    def list_by_type(self, entity_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT * FROM entities WHERE type = ? LIMIT ?", (entity_type, limit))
            return [{"id": r[0], "type": r[1], "data": r[2]} for r in cursor.fetchall()]
        finally:
            self._return_conn(conn)

if __name__ == "__main__":
    print("DBPersistence self-test")
    db = DBPersistence(":memory:")
    db.create("test_1", "user", {"name": "Alice"})
    result = db.read("test_1")
    assert result is not None
    assert result["type"] == "user"
    print("All tests pass")
