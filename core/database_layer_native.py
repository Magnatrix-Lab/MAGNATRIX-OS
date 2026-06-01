#!/usr/bin/env python3
"""
core/database_layer_native.py
MAGNATRIX-OS — Database Layer for Local-First Persistence
AMATI pattern: SQLite, migrations, FTS, structured logging

Pure Python, sqlite3 only. Simulates connection pooling, schema management,
CRUD operations, and full-text search.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _fmt_time(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


# ───────────────────────────────────────────────────────────────
# 1. CONNECTION MANAGER
# ───────────────────────────────────────────────────────────────

class ConnectionManager:
    """SQLite connection with WAL mode and health checks."""

    def __init__(self, db_path: str = "magnatrix.db") -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def health_check(self) -> bool:
        try:
            conn = self.connect()
            conn.execute("SELECT 1")
            return True
        except Exception:
            return False


# ───────────────────────────────────────────────────────────────
# 2. SCHEMA MANAGER
# ───────────────────────────────────────────────────────────────

class SchemaManager:
    """Create and manage database schema."""

    SCHEMA = {
        "sessions": """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                model_id TEXT,
                messages TEXT,
                token_count INTEGER,
                created_at REAL,
                updated_at REAL
            )
        """,
        "knowledge": """
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                key TEXT,
                value TEXT,
                category TEXT,
                tags TEXT,
                created_at REAL
            )
        """,
        "logs": """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                module TEXT,
                message TEXT,
                timestamp REAL
            )
        """,
        "users": """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT,
                preferences TEXT,
                created_at REAL
            )
        """,
        "migrations": """
            CREATE TABLE IF NOT EXISTS migrations (
                version INTEGER PRIMARY KEY,
                applied_at REAL
            )
        """,
    }

    def __init__(self, conn: ConnectionManager) -> None:
        self.conn = conn

    def create_all(self) -> None:
        conn = self.conn.connect()
        for name, sql in self.SCHEMA.items():
            conn.execute(sql)
        conn.commit()

    def drop_all(self) -> None:
        conn = self.conn.connect()
        for name in reversed(list(self.SCHEMA.keys())):
            conn.execute(f"DROP TABLE IF EXISTS {name}")
        conn.commit()

    def version(self) -> int:
        conn = self.conn.connect()
        try:
            row = conn.execute("SELECT MAX(version) FROM migrations").fetchone()
            return row[0] or 0
        except Exception:
            return 0


# ───────────────────────────────────────────────────────────────
# 3. SESSION STORE
# ───────────────────────────────────────────────────────────────

class SessionStore:
    """CRUD for session data."""

    def __init__(self, conn: ConnectionManager) -> None:
        self.conn = conn

    def create(self, session_id: str, user_id: str, model_id: str, messages: List[Dict[str, str]]) -> bool:
        conn = self.conn.connect()
        conn.execute(
            "INSERT INTO sessions (id, user_id, model_id, messages, token_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, user_id, model_id, json.dumps(messages), sum(len(m["content"]) for m in messages) // 4, _now(), _now()),
        )
        conn.commit()
        return True

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        conn = self.conn.connect()
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row:
            return {"id": row[0], "user_id": row[1], "model_id": row[2], "messages": json.loads(row[3]), "token_count": row[4], "created_at": row[5]}
        return None

    def update(self, session_id: str, messages: List[Dict[str, str]]) -> bool:
        conn = self.conn.connect()
        conn.execute(
            "UPDATE sessions SET messages = ?, token_count = ?, updated_at = ? WHERE id = ?",
            (json.dumps(messages), sum(len(m["content"]) for m in messages) // 4, _now(), session_id),
        )
        conn.commit()
        return True

    def list(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self.conn.connect()
        rows = conn.execute("SELECT id, user_id, model_id, token_count, created_at FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r[0], "user_id": r[1], "model_id": r[2], "token_count": r[3], "created_at": r[4]} for r in rows]


# ───────────────────────────────────────────────────────────────
# 4. KNOWLEDGE STORE
# ───────────────────────────────────────────────────────────────

class KnowledgeStoreDB:
    """CRUD for knowledge entries with FTS."""

    def __init__(self, conn: ConnectionManager) -> None:
        self.conn = conn

    def create(self, key: str, value: str, category: str = "general", tags: Optional[List[str]] = None) -> bool:
        conn = self.conn.connect()
        conn.execute(
            "INSERT INTO knowledge (id, key, value, category, tags, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (f"k_{key}", key, value, category, json.dumps(tags or []), _now()),
        )
        conn.commit()
        return True

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self.conn.connect()
        # Simple LIKE search (FTS simulation)
        rows = conn.execute(
            "SELECT key, value, category, tags FROM knowledge WHERE key LIKE ? OR value LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [{"key": r[0], "value": r[1], "category": r[2], "tags": json.loads(r[3])} for r in rows]

    def list_by_category(self, category: str) -> List[Dict[str, Any]]:
        conn = self.conn.connect()
        rows = conn.execute("SELECT key, value, tags FROM knowledge WHERE category = ?", (category,)).fetchall()
        return [{"key": r[0], "value": r[1], "tags": json.loads(r[2])} for r in rows]


# ───────────────────────────────────────────────────────────────
# 5. LOG STORE
# ───────────────────────────────────────────────────────────────

class LogStore:
    """Structured logging with filtering and rotation."""

    LEVELS = ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]

    def __init__(self, conn: ConnectionManager) -> None:
        self.conn = conn

    def log(self, level: str, module: str, message: str) -> bool:
        conn = self.conn.connect()
        conn.execute("INSERT INTO logs (level, module, message, timestamp) VALUES (?, ?, ?, ?)", (level, module, message, _now()))
        conn.commit()
        return True

    def get_logs(self, level: Optional[str] = None, module: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self.conn.connect()
        query = "SELECT level, module, message, timestamp FROM logs WHERE 1=1"
        params = []
        if level:
            query += " AND level = ?"
            params.append(level)
        if module:
            query += " AND module = ?"
            params.append(module)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [{"level": r[0], "module": r[1], "message": r[2], "timestamp": r[3]} for r in rows]

    def export_json(self, filepath: str) -> bool:
        logs = self.get_logs(limit=10000)
        with open(filepath, "w") as f:
            json.dump(logs, f, indent=2)
        return True


# ───────────────────────────────────────────────────────────────
# 6. MIGRATION ENGINE
# ───────────────────────────────────────────────────────────────

class MigrationEngine:
    """Track and apply schema migrations."""

    def __init__(self, conn: ConnectionManager) -> None:
        self.conn = conn

    def get_version(self) -> int:
        conn = self.conn.connect()
        try:
            row = conn.execute("SELECT MAX(version) FROM migrations").fetchone()
            return row[0] or 0
        except Exception:
            return 0

    def migrate(self, target_version: int) -> bool:
        current = self.get_version()
        if current >= target_version:
            return False
        conn = self.conn.connect()
        for v in range(current + 1, target_version + 1):
            # Simulated migrations - check if column exists first
            try:
                conn.execute("SELECT metadata FROM sessions LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE sessions ADD COLUMN metadata TEXT DEFAULT '{}' ")
            conn.execute("INSERT INTO migrations (version, applied_at) VALUES (?, ?)", (v, _now()))
        conn.commit()
        return True


# ───────────────────────────────────────────────────────────────
# 7. DATABASE LAYER
# ───────────────────────────────────────────────────────────────

class DatabaseLayer:
    """Main orchestrator: connect -> schema -> migrate -> store -> query -> log."""

    def __init__(self, db_path: str = "magnatrix.db") -> None:
        self.conn = ConnectionManager(db_path)
        self.schema = SchemaManager(self.conn)
        self.sessions = SessionStore(self.conn)
        self.knowledge = KnowledgeStoreDB(self.conn)
        self.logs = LogStore(self.conn)
        self.migrations = MigrationEngine(self.conn)

    def init(self) -> None:
        self.schema.create_all()
        self.migrations.migrate(1)

    def reset(self) -> None:
        self.schema.drop_all()
        self.schema.create_all()

    def health(self) -> Dict[str, Any]:
        return {
            "connected": self.conn.health_check(),
            "schema_version": self.migrations.get_version(),
            "tables": ["sessions", "knowledge", "logs", "users", "migrations"],
        }

    def stats(self) -> Dict[str, Any]:
        conn = self.conn.connect()
        counts = {}
        for table in ["sessions", "knowledge", "logs", "users"]:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                counts[table] = row[0]
            except Exception:
                counts[table] = 0
        return counts

    def close(self) -> None:
        self.conn.close()


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Database Layer Demo")
    print("=" * 60)

    db = DatabaseLayer(db_path=":memory:")
    db.init()

    print("\n[1] Health Check")
    print(f"  {json.dumps(db.health(), indent=2)}")

    print("\n[2] Create Sessions")
    db.sessions.create("sess_1", "user_1", "magnatrix-7b", [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi!"}])
    db.sessions.create("sess_2", "user_2", "claude-3-5", [{"role": "user", "content": "What is AI?"}])
    print(f"  Sessions created: 2")

    print("\n[3] List Sessions")
    sessions = db.sessions.list()
    for s in sessions:
        print(f"  {s['id']}: user={s['user_id']}, model={s['model_id']}, tokens={s['token_count']}")

    print("\n[4] Knowledge Store")
    db.knowledge.create("python_lambda", "Anonymous functions in Python", "coding", ["python", "functions"])
    db.knowledge.create("ai_definition", "Artificial intelligence is...", "ai", ["ai", "definition"])
    results = db.knowledge.search("python")
    print(f"  Search 'python': {len(results)} results")
    for r in results:
        print(f"    {r['key']}: {r['value'][:40]}...")

    print("\n[5] Logs")
    db.logs.log("INFO", "arena", "Arena started")
    db.logs.log("WARN", "model", "Model latency high")
    db.logs.log("ERROR", "cache", "Cache miss")
    logs = db.logs.get_logs(level="INFO")
    print(f"  INFO logs: {len(logs)}")
    for l in logs:
        print(f"    [{l['level']}] {l['module']}: {l['message']}")

    print("\n[6] Stats")
    print(f"  {json.dumps(db.stats(), indent=2)}")

    print("\n[7] Migration")
    print(f"  Current version: {db.migrations.get_version()}")
    db.migrations.migrate(2)
    print(f"  After migration: {db.migrations.get_version()}")

    db.close()

    print("\n" + "=" * 60)
    print("Demo complete. Database Layer ready for MAGNATRIX-OS.")
    print("=" * 60)
