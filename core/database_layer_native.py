#!/usr/bin/env python3
"""
Database Layer for MAGNATRIX-OS
SQLite ORM with query builder, migration system, transaction support,
and schema validation. Native stdlib only (sqlite3 built-in).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union

T = TypeVar("T")


class ColumnType(enum.Enum):
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    REAL = "REAL"
    BLOB = "BLOB"
    BOOLEAN = "BOOLEAN"
    JSON = "TEXT"  # stored as JSON string
    TIMESTAMP = "REAL"  # stored as unix timestamp


@dataclasses.dataclass
class Column:
    name: str
    col_type: ColumnType
    primary_key: bool = False
    nullable: bool = True
    default: Any = None
    unique: bool = False
    index: bool = False


@dataclasses.dataclass
class Schema:
    table_name: str
    columns: List[Column]
    version: int = 1


class Migration:
    """Base class for schema migrations."""

    def __init__(self, version: int, description: str) -> None:
        self.version = version
        self.description = description

    def up(self, conn: sqlite3.Connection) -> None:
        raise NotImplementedError

    def down(self, conn: sqlite3.Connection) -> None:
        raise NotImplementedError


class DatabaseManager:
    """Central database manager with ORM, query builder, and migrations."""

    def __init__(self, db_path: str = "magnatrix.db") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._migrations: List[Migration] = []
        self._ensure_migration_table()

    def _ensure_migration_table(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS __migrations (
                version INTEGER PRIMARY KEY,
                applied_at REAL,
                description TEXT
            )
        """)
        self._conn.commit()

    def _get_current_version(self) -> int:
        cursor = self._conn.execute("SELECT MAX(version) as v FROM __migrations")
        row = cursor.fetchone()
        return row["v"] or 0 if row else 0

    def register_migration(self, migration: Migration) -> None:
        self._migrations.append(migration)
        self._migrations.sort(key=lambda m: m.version)

    def migrate(self) -> List[int]:
        """Run all pending migrations. Returns applied versions."""
        current = self._get_current_version()
        applied: List[int] = []
        with self._lock:
            for mig in self._migrations:
                if mig.version > current:
                    mig.up(self._conn)
                    self._conn.execute(
                        "INSERT INTO __migrations (version, applied_at, description) VALUES (?, ?, ?)",
                        (mig.version, time.time(), mig.description)
                    )
                    self._conn.commit()
                    applied.append(mig.version)
        return applied

    def rollback(self, target_version: int) -> List[int]:
        """Rollback migrations down to target_version."""
        current = self._get_current_version()
        rolled: List[int] = []
        with self._lock:
            for mig in reversed(self._migrations):
                if mig.version <= current and mig.version > target_version:
                    mig.down(self._conn)
                    self._conn.execute("DELETE FROM __migrations WHERE version = ?", (mig.version,))
                    self._conn.commit()
                    rolled.append(mig.version)
        return rolled

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def create_table(self, schema: Schema) -> None:
        col_defs = []
        for col in schema.columns:
            defn = f"{col.name} {col.col_type.value}"
            if col.primary_key:
                defn += " PRIMARY KEY"
            if not col.nullable and not col.primary_key:
                defn += " NOT NULL"
            if col.unique and not col.primary_key:
                defn += " UNIQUE"
            if col.default is not None:
                defn += f" DEFAULT {json.dumps(col.default) if isinstance(col.default, str) else col.default}"
            col_defs.append(defn)
        sql = f"CREATE TABLE IF NOT EXISTS {schema.table_name} ({', '.join(col_defs)})"
        with self._lock:
            self._conn.execute(sql)
            self._conn.commit()
        # Create indexes
        for col in schema.columns:
            if col.index:
                self._conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{schema.table_name}_{col.name} ON {schema.table_name}({col.name})")
        self._conn.commit()

    def drop_table(self, table_name: str) -> None:
        with self._lock:
            self._conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            self._conn.commit()

    # ------------------------------------------------------------------
    # Query builder
    # ------------------------------------------------------------------

    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        keys = list(data.keys())
        placeholders = ", ".join(["?"] * len(keys))
        values = []
        for k in keys:
            v = data[k]
            if isinstance(v, (dict, list)):
                v = json.dumps(v)
            values.append(v)
        sql = f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({placeholders})"
        with self._lock:
            cursor = self._conn.execute(sql, values)
            self._conn.commit()
            return cursor.lastrowid or 0

    def insert_many(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        if not rows:
            return 0
        keys = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(keys))
        sql = f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({placeholders})"
        with self._lock:
            cursor = self._conn.executemany(sql, [
                [json.dumps(r[k]) if isinstance(r[k], (dict, list)) else r[k] for k in keys]
                for r in rows
            ])
            self._conn.commit()
            return cursor.rowcount

    def select(self, table_name: str, where: Optional[Dict[str, Any]] = None, order_by: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM {table_name}"
        params = []
        if where:
            conditions = []
            for k, v in where.items():
                conditions.append(f"{k} = ?")
                params.append(v)
            sql += " WHERE " + " AND ".join(conditions)
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"
        with self._lock:
            cursor = self._conn.execute(sql, params)
            rows = [dict(row) for row in cursor.fetchall()]
        # Try JSON decode for text columns
        for row in rows:
            for k, v in row.items():
                if isinstance(v, str) and (v.startswith("{") or v.startswith("[")):
                    try:
                        row[k] = json.loads(v)
                    except Exception:
                        pass
        return rows

    def update(self, table_name: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
        set_clauses = []
        values = []
        for k, v in data.items():
            set_clauses.append(f"{k} = ?")
            values.append(json.dumps(v) if isinstance(v, (dict, list)) else v)
        conditions = []
        for k, v in where.items():
            conditions.append(f"{k} = ?")
            values.append(v)
        sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {' AND '.join(conditions)}"
        with self._lock:
            cursor = self._conn.execute(sql, values)
            self._conn.commit()
            return cursor.rowcount

    def delete(self, table_name: str, where: Dict[str, Any]) -> int:
        conditions = []
        values = []
        for k, v in where.items():
            conditions.append(f"{k} = ?")
            values.append(v)
        sql = f"DELETE FROM {table_name} WHERE {' AND '.join(conditions)}"
        with self._lock:
            cursor = self._conn.execute(sql, values)
            self._conn.commit()
            return cursor.rowcount

    def query(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
        with self._lock:
            cursor = self._conn.execute(sql, params or ())
            return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Transaction
    # ------------------------------------------------------------------

    def begin(self) -> None:
        self._conn.execute("BEGIN")

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        cursor = self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cursor.fetchall()]
        table_counts = {}
        for t in tables:
            try:
                c = self._conn.execute(f"SELECT COUNT(*) as cnt FROM {t}")
                table_counts[t] = c.fetchone()["cnt"]
            except Exception:
                table_counts[t] = -1
        return {
            "db_path": self.db_path,
            "tables": tables,
            "table_counts": table_counts,
            "migrations_applied": self._get_current_version(),
        }

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile, os
    tmp = tempfile.mktemp(suffix=".db")
    db = DatabaseManager(tmp)
    print("=== Database Layer Demo ===\n")
    # Create table
    schema = Schema("users", [
        Column("id", ColumnType.INTEGER, primary_key=True, nullable=False),
        Column("username", ColumnType.TEXT, nullable=False, unique=True),
        Column("email", ColumnType.TEXT, nullable=False),
        Column("metadata", ColumnType.JSON, default={}),
        Column("created_at", ColumnType.TIMESTAMP, default=0.0),
    ])
    db.create_table(schema)
    # Insert
    db.insert("users", {
        "username": "admin",
        "email": "admin@magnatrix.io",
        "metadata": {"role": "admin"},
        "created_at": time.time(),
    })
    db.insert("users", {
        "username": "guest",
        "email": "guest@magnatrix.io",
        "metadata": {"role": "guest"},
        "created_at": time.time(),
    })
    # Select
    rows = db.select("users")
    print(f"Inserted {len(rows)} users:")
    for r in rows:
        print(f"  {r}")
    # Update
    db.update("users", {"email": "admin@new.io"}, {"username": "admin"})
    # Select with where
    rows = db.select("users", where={"username": "admin"})
    print(f"\nUpdated admin: {rows[0]}")
    # Stats
    print(f"\nStats: {db.stats()}")
    # Cleanup
    db.close()
    os.remove(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
