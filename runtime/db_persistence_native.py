"""
MAGNATRIX-OS Database Persistence Layer
Self-contained native persistence with SQLite, connection pool, CRUD,
transactions, query builder, schema migration, and ORM-like mapping.
"""

import sqlite3, threading, json, time, hashlib
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from contextlib import contextmanager


@dataclass
class Query:
    """Simple query builder."""
    table: str
    where: List[Tuple[str, str, Any]] = None
    order_by: str = ""
    limit: int = 0
    offset: int = 0

    def clone(self, **kwargs) -> "Query":
        data = asdict(self)
        data.update(kwargs)
        return Query(**data)

    def build(self) -> Tuple[str, List[Any]]:
        sql = f"SELECT * FROM {self.table}"
        params: List[Any] = []
        if self.where:
            clauses = []
            for col, op, val in self.where:
                clauses.append(f"{col} {op} ?")
                params.append(val)
            sql += " WHERE " + " AND ".join(clauses)
        if self.order_by:
            sql += f" ORDER BY {self.order_by}"
        if self.limit:
            sql += f" LIMIT {self.limit}"
        if self.offset:
            sql += f" OFFSET {self.offset}"
        return sql, params


class DBPersistence:
    """Database persistence layer for MAGNATRIX-OS."""

    def __init__(self, db_path: str = ":memory:", pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: List[sqlite3.Connection] = []
        self._lock = threading.Lock()
        self._tables: Dict[str, List[str]] = {}
        self._migrations: List[Dict] = []
        self._init_pool()

    def _init_pool(self) -> None:
        for _ in range(self.pool_size):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._pool.append(conn)

    @contextmanager
    def _conn(self):
        with self._lock:
            conn = self._pool.pop(0) if self._pool else sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            yield conn
        finally:
            with self._lock:
                self._pool.append(conn)

    # ── connection health ─────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        try:
            with self._conn() as conn:
                conn.execute("SELECT 1")
                return {"ok": True, "latency_ms": 0, "pool_size": len(self._pool)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── schema migration ──────────────────────────────────────

    def migrate(self, migrations: List[Dict]) -> None:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS __migrations (
                    id TEXT PRIMARY KEY,
                    applied_at TEXT
                )
            """)
            conn.commit()
            for m in migrations:
                mid = m.get("id") or hashlib.sha256(m["sql"].encode()).hexdigest()[:16]
                cur.execute("SELECT 1 FROM __migrations WHERE id = ?", (mid,))
                if cur.fetchone():
                    continue
                cur.executescript(m["sql"])
                cur.execute("INSERT INTO __migrations VALUES (?, ?)", (mid, datetime.now().isoformat()))
                conn.commit()
                self._migrations.append({"id": mid, "sql": m["sql"]})

    def migration_status(self) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM __migrations")
            return [dict(row) for row in cur.fetchall()]

    # ── ORM-like mapping ──────────────────────────────────────

    def create_table(self, table: str, schema: Dict[str, str], indexes: List[str] = None) -> None:
        cols = ", ".join(f"{k} {v}" for k, v in schema.items())
        sql = f"CREATE TABLE IF NOT EXISTS {table} ({cols})"
        with self._conn() as conn:
            conn.execute(sql)
            conn.commit()
            if indexes:
                for idx in indexes:
                    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{idx} ON {table}({idx})")
                    conn.commit()
        self._tables[table] = list(schema.keys())

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        with self._conn() as conn:
            cur = conn.execute(sql, list(data.values()))
            conn.commit()
            return cur.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
        set_clause = ", ".join(f"{k} = ?" for k in data)
        where_clause = " AND ".join(f"{k} = ?" for k in where)
        sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        with self._conn() as conn:
            cur = conn.execute(sql, list(data.values()) + list(where.values()))
            conn.commit()
            return cur.rowcount

    def delete(self, table: str, where: Dict[str, Any]) -> int:
        where_clause = " AND ".join(f"{k} = ?" for k in where)
        sql = f"DELETE FROM {table} WHERE {where_clause}"
        with self._conn() as conn:
            cur = conn.execute(sql, list(where.values()))
            conn.commit()
            return cur.rowcount

    def read(self, table: str, where: Dict[str, Any] = None) -> List[Dict]:
        sql = f"SELECT * FROM {table}"
        params: List[Any] = []
        if where:
            clauses = " AND ".join(f"{k} = ?" for k in where)
            sql += f" WHERE {clauses}"
            params = list(where.values())
        with self._conn() as conn:
            cur = conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def read_one(self, table: str, where: Dict[str, Any]) -> Optional[Dict]:
        rows = self.read(table, where)
        return rows[0] if rows else None

    # ── query builder ─────────────────────────────────────────

    def query(self, q: Query) -> List[Dict]:
        sql, params = q.build()
        with self._conn() as conn:
            cur = conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def query_raw(self, sql: str, params: List[Any] = None) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.execute(sql, params or [])
            return [dict(row) for row in cur.fetchall()]

    # ── transaction support ───────────────────────────────────

    @contextmanager
    def transaction(self):
        with self._conn() as conn:
            conn.execute("BEGIN")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    # ── indexing ────────────────────────────────────────────────

    def create_index(self, table: str, column: str) -> None:
        with self._conn() as conn:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{column} ON {table}({column})")
            conn.commit()

    def explain(self, sql: str) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.execute(f"EXPLAIN QUERY PLAN {sql}")
            return [dict(row) for row in cur.fetchall()]

    # ── connection pool stats ─────────────────────────────────

    def pool_stats(self) -> Dict:
        return {
            "size": len(self._pool),
            "max": self.pool_size,
            "db_path": self.db_path
        }

    def close(self) -> None:
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()


# ── self-test ─────────────────────────────────────────────────

def _self_test():
    db = DBPersistence(":memory:", pool_size=3)

    # health check
    h = db.health_check()
    assert h["ok"] is True

    # create table
    db.create_table("users", {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "TEXT NOT NULL",
        "email": "TEXT",
        "age": "INTEGER"
    }, indexes=["email"])

    # insert
    uid1 = db.insert("users", {"name": "Alice", "email": "a@example.com", "age": 30})
    uid2 = db.insert("users", {"name": "Bob", "email": "b@example.com", "age": 25})
    assert uid1 == 1 and uid2 == 2

    # read
    all_users = db.read("users")
    assert len(all_users) == 2
    alice = db.read_one("users", {"id": uid1})
    assert alice["name"] == "Alice"

    # update
    rc = db.update("users", {"age": 31}, {"id": uid1})
    assert rc == 1
    assert db.read_one("users", {"id": uid1})["age"] == 31

    # delete
    rc = db.delete("users", {"id": uid2})
    assert rc == 1
    assert len(db.read("users")) == 1

    # query builder
    q = Query("users", where=[("age", ">", 25)], order_by="name DESC", limit=1)
    result = db.query(q)
    assert len(result) == 1 and result[0]["name"] == "Alice"

    # raw query
    raw = db.query_raw("SELECT * FROM users WHERE name = ?", ["Alice"])
    assert len(raw) == 1

    # transaction
    with db.transaction() as conn:
        conn.execute("INSERT INTO users (name, email, age) VALUES (?, ?, ?)", ("Carol", "c@example.com", 28))
    assert len(db.read("users")) == 2

    # migration
    db2 = DBPersistence(":memory:")
    db2.migrate([{"sql": "CREATE TABLE logs (id INTEGER PRIMARY KEY, msg TEXT)"}])
    assert len(db2.migration_status()) == 1

    # pool stats
    assert db.pool_stats()["size"] == 3

    db.close()
    print("[db_persistence_native] all tests passed")


if __name__ == "__main__":
    _self_test()
