#!/usr/bin/env python3
"""
Database Abstraction Layer for MAGNATRIX-OS
SQLite wrapper, query builder, schema migration, ORM-lite.
Pure stdlib -- uses sqlite3 built-in.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
import sqlite3
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class SQLOperation(enum.Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclasses.dataclass
class Column:
    name: str
    type: str = "TEXT"
    primary_key: bool = False
    auto_increment: bool = False
    not_null: bool = False
    default: Any = None
    unique: bool = False
    index: bool = False


@dataclasses.dataclass
class TableSchema:
    name: str
    columns: List[Column] = dataclasses.field(default_factory=list)

    def to_sql(self) -> str:
        cols = []
        for c in self.columns:
            col_str = f"{c.name} {c.type}"
            if c.primary_key:
                col_str += " PRIMARY KEY"
            if c.auto_increment:
                col_str += " AUTOINCREMENT"
            if c.not_null:
                col_str += " NOT NULL"
            if c.default is not None:
                col_str += f" DEFAULT {c.default}"
            if c.unique:
                col_str += " UNIQUE"
            cols.append(col_str)
        return f"CREATE TABLE IF NOT EXISTS {self.name} ({', '.join(cols)})"


class QueryBuilder:
    """Fluent SQL query builder."""

    def __init__(self, table: str) -> None:
        self._table = table
        self._operation: Optional[SQLOperation] = None
        self._select_cols: List[str] = ["*"]
        self._values: Dict[str, Any] = {}
        self._where: List[Tuple[str, str, Any]] = []
        self._order_by: Optional[str] = None
        self._order_desc: bool = False
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._joins: List[str] = []

    def select(self, *columns: str) -> QueryBuilder:
        self._operation = SQLOperation.SELECT
        self._select_cols = list(columns) if columns else ["*"]
        return self

    def insert(self, **values: Any) -> QueryBuilder:
        self._operation = SQLOperation.INSERT
        self._values = values
        return self

    def update(self, **values: Any) -> QueryBuilder:
        self._operation = SQLOperation.UPDATE
        self._values = values
        return self

    def delete(self) -> QueryBuilder:
        self._operation = SQLOperation.DELETE
        return self

    def where(self, column: str, operator: str, value: Any) -> QueryBuilder:
        self._where.append((column, operator, value))
        return self

    def order_by(self, column: str, desc: bool = False) -> QueryBuilder:
        self._order_by = column
        self._order_desc = desc
        return self

    def limit(self, n: int) -> QueryBuilder:
        self._limit = n
        return self

    def offset(self, n: int) -> QueryBuilder:
        self._offset = n
        return self

    def join(self, table: str, on: str) -> QueryBuilder:
        self._joins.append(f"JOIN {table} ON {on}")
        return self

    def to_sql(self) -> Tuple[str, Tuple[Any, ...]]:
        if self._operation == SQLOperation.SELECT:
            sql = f"SELECT {', '.join(self._select_cols)} FROM {self._table}"
            if self._joins:
                sql += " " + " ".join(self._joins)
            params: Tuple[Any, ...] = ()
            if self._where:
                conditions = []
                params = tuple()
                for col, op, val in self._where:
                    conditions.append(f"{col} {op} ?")
                    params = params + (val,)
                sql += " WHERE " + " AND ".join(conditions)
            if self._order_by:
                sql += f" ORDER BY {self._order_by} {'DESC' if self._order_desc else 'ASC'}"
            if self._limit is not None:
                sql += f" LIMIT {self._limit}"
            if self._offset is not None:
                sql += f" OFFSET {self._offset}"
            return sql, params

        elif self._operation == SQLOperation.INSERT:
            cols = list(self._values.keys())
            placeholders = ["?"] * len(cols)
            sql = f"INSERT INTO {self._table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
            return sql, tuple(self._values.values())

        elif self._operation == SQLOperation.UPDATE:
            set_clauses = [f"{k} = ?" for k in self._values.keys()]
            sql = f"UPDATE {self._table} SET {', '.join(set_clauses)}"
            params = tuple(self._values.values())
            if self._where:
                conditions = []
                for col, op, val in self._where:
                    conditions.append(f"{col} {op} ?")
                    params = params + (val,)
                sql += " WHERE " + " AND ".join(conditions)
            return sql, params

        elif self._operation == SQLOperation.DELETE:
            sql = f"DELETE FROM {self._table}"
            params = ()
            if self._where:
                conditions = []
                for col, op, val in self._where:
                    conditions.append(f"{col} {op} ?")
                    params = params + (val,)
                sql += " WHERE " + " AND ".join(conditions)
            return sql, params

        return "", ()


class DatabaseConnection:
    """SQLite connection wrapper with pooling."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self.connect()
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            conn.commit()
            return [dict(row) for row in rows]

    def execute_raw(self, sql: str) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self.connect()
            cursor = conn.execute(sql)
            rows = cursor.fetchall()
            conn.commit()
            return [dict(row) for row in rows]


class SchemaManager:
    """Schema migration management."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self._ensure_migration_table()

    def _ensure_migration_table(self) -> None:
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS __migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                applied_at REAL NOT NULL,
                checksum TEXT NOT NULL
            )
        """)

    def create_table(self, schema: TableSchema) -> None:
        sql = schema.to_sql()
        self._db.execute_raw(sql)

    def apply_migration(self, name: str, up_sql: str, down_sql: str = "") -> bool:
        # Check if already applied
        existing = self._db.execute("SELECT * FROM __migrations WHERE name = ?", (name,))
        if existing:
            return False

        # Apply migration
        checksum = hashlib.sha256(up_sql.encode()).hexdigest()[:16]
        self._db.execute_raw(up_sql)
        self._db.execute(
            "INSERT INTO __migrations (name, applied_at, checksum) VALUES (?, ?, ?)",
            (name, time.time(), checksum),
        )
        return True

    def rollback_migration(self, name: str) -> bool:
        existing = self._db.execute("SELECT * FROM __migrations WHERE name = ?", (name,))
        if not existing:
            return False

        self._db.execute("DELETE FROM __migrations WHERE name = ?", (name,))
        return True

    def list_migrations(self) -> List[Dict[str, Any]]:
        return self._db.execute("SELECT * FROM __migrations ORDER BY applied_at")


class ModelManager:
    """Lightweight ORM for CRUD operations."""

    def __init__(self, db: DatabaseConnection, schema: TableSchema) -> None:
        self._db = db
        self._schema = schema

    def create(self, **values: Any) -> Dict[str, Any]:
        qb = QueryBuilder(self._schema.name).insert(**values)
        sql, params = qb.to_sql()
        self._db.execute(sql, params)
        return values

    def find(self, pk_value: Any) -> Optional[Dict[str, Any]]:
        pk_col = None
        for c in self._schema.columns:
            if c.primary_key:
                pk_col = c.name
                break
        if not pk_col:
            return None

        qb = QueryBuilder(self._schema.name).select().where(pk_col, "=", pk_value).limit(1)
        sql, params = qb.to_sql()
        results = self._db.execute(sql, params)
        return results[0] if results else None

    def find_all(self, **filters: Any) -> List[Dict[str, Any]]:
        qb = QueryBuilder(self._schema.name).select()
        for col, val in filters.items():
            qb = qb.where(col, "=", val)
        sql, params = qb.to_sql()
        return self._db.execute(sql, params)

    def update(self, pk_value: Any, **values: Any) -> bool:
        pk_col = None
        for c in self._schema.columns:
            if c.primary_key:
                pk_col = c.name
                break
        if not pk_col:
            return False

        qb = QueryBuilder(self._schema.name).update(**values).where(pk_col, "=", pk_value)
        sql, params = qb.to_sql()
        self._db.execute(sql, params)
        return True

    def delete(self, pk_value: Any) -> bool:
        pk_col = None
        for c in self._schema.columns:
            if c.primary_key:
                pk_col = c.name
                break
        if not pk_col:
            return False

        qb = QueryBuilder(self._schema.name).delete().where(pk_col, "=", pk_value)
        sql, params = qb.to_sql()
        self._db.execute(sql, params)
        return True


class DatabaseAbstraction:
    """Main database abstraction orchestrator."""

    def __init__(self, db_path: str = "./magnatrix.db") -> None:
        self.db = DatabaseConnection(db_path)
        self.schema = SchemaManager(self.db)
        self._models: Dict[str, ModelManager] = {}

    def define_model(self, schema: TableSchema) -> ModelManager:
        self.schema.create_table(schema)
        model = ModelManager(self.db, schema)
        self._models[schema.name] = model
        return model

    def query(self, table: str) -> QueryBuilder:
        return QueryBuilder(table)

    def raw(self, sql: str) -> List[Dict[str, Any]]:
        return self.db.execute_raw(sql)

    def close(self) -> None:
        self.db.close()

    def transaction(self) -> "TransactionContext":
        return TransactionContext(self.db)


class TransactionContext:
    """Context manager for database transactions."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def __enter__(self) -> TransactionContext:
        self._db.execute_raw("BEGIN")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self._db.execute_raw("COMMIT")
        else:
            self._db.execute_raw("ROLLBACK")


def _demo() -> None:
    print("=== Database Abstraction Layer Demo ===\n")

    db = DatabaseAbstraction(":memory:")

    # Define a model
    print("--- Defining Model ---")
    user_schema = TableSchema("users", [
        Column("id", "INTEGER", primary_key=True, auto_increment=True),
        Column("name", "TEXT", not_null=True),
        Column("email", "TEXT", unique=True),
        Column("age", "INTEGER"),
        Column("created_at", "REAL", default="0.0"),
    ])
    users = db.define_model(user_schema)
    print("  Created 'users' table\n")

    # Create records
    print("--- Creating Records ---")
    users.create(name="Alice", email="alice@example.com", age=30, created_at=time.time())
    users.create(name="Bob", email="bob@example.com", age=25, created_at=time.time())
    users.create(name="Charlie", email="charlie@example.com", age=35, created_at=time.time())
    print("  Created 3 users\n")

    # Query builder
    print("--- Query Builder ---")
    qb = db.query("users").select("name", "email").where("age", ">", 25).order_by("age", desc=True)
    sql, params = qb.to_sql()
    print(f"  SQL: {sql}")
    print(f"  Params: {params}")
    results = db.db.execute(sql, params)
    print(f"  Results: {len(results)}")
    for r in results:
        print(f"    {r['name']}: {r['email']}")
    print()

    # Find by ID
    print("--- Find by ID ---")
    user = users.find(1)
    print(f"  User 1: {user['name'] if user else 'Not found'}\n")

    # Update
    print("--- Update ---")
    users.update(1, age=31)
    user = users.find(1)
    print(f"  Updated age: {user['age'] if user else 'N/A'}\n")

    # Delete
    print("--- Delete ---")
    users.delete(2)
    all_users = users.find_all()
    print(f"  Remaining users: {len(all_users)}\n")

    # Migration
    print("--- Migration ---")
    db.schema.apply_migration("add_posts_table", """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("  Applied migration: add_posts_table")
    migrations = db.schema.list_migrations()
    print(f"  Total migrations: {len(migrations)}\n")

    # Transaction
    print("--- Transaction ---")
    with db.transaction():
        db.db.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Dave", "dave@example.com"))
    print("  Transaction committed\n")

    # Stats
    print("--- Stats ---")
    all_users = users.find_all()
    print(f"  Total users: {len(all_users)}")
    print(f"  Tables: users, posts, __migrations")
    print()

    db.close()
    print("=== Database Abstraction Demo Complete ===")


if __name__ == "__main__":
    _demo()
