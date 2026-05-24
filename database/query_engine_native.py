#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Query Engine (Layer 5 Extension)
SQL-like Query Engine for Knowledge Graph + Vector Hybrid Queries
================================================================================
Zero-dependency query parser, planner, and execution engine.
================================================================================
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import operator
import re
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union


# =============================================================================
# AST Nodes
# =============================================================================
@dataclass
class QSelect:
    columns: List[str]
    from_table: str
    where: Optional[QWhere] = None
    order_by: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


@dataclass
class QWhere:
    left: str
    op: str
    right: Union[str, int, float, bool]


@dataclass
class QInsert:
    into_table: str
    values: Dict[str, Any]


@dataclass
class QDelete:
    from_table: str
    where: Optional[QWhere] = None


# =============================================================================
# Query Parser
# =============================================================================
class QueryParser:
    """Parses MAGNATRIX-QL (SQL subset) into AST."""

    TOKENS = re.compile(
        r"SELECT|INSERT|DELETE|FROM|WHERE|ORDER\s+BY|LIMIT|OFFSET|INTO|VALUES|"
        r"AND|OR|NOT|ASC|DESC|TRUE|FALSE|NULL|"
        r"[a-zA-Z_][a-zA-Z0-9_]*|\*|>=|<=|!=|=|<|>|\d+\.?\d*|'[^']*'|\(|\)|,|;"
    )

    def parse(self, sql: str) -> Union[QSelect, QInsert, QDelete]:
        tokens = [t.upper() if t.upper() in ("SELECT", "FROM", "WHERE", "LIMIT", "OFFSET", "ORDER", "BY", "INSERT", "INTO", "VALUES", "DELETE", "AND", "OR", "NOT", "ASC", "DESC", "TRUE", "FALSE", "NULL") else t for t in self.TOKENS.findall(sql)]
        if not tokens:
            raise SyntaxError("Empty query")
        if tokens[0] == "SELECT":
            return self._parse_select(tokens)
        if tokens[0] == "INSERT":
            return self._parse_insert(tokens)
        if tokens[0] == "DELETE":
            return self._parse_delete(tokens)
        raise SyntaxError(f"Unknown statement: {tokens[0]}")

    def _parse_select(self, tokens: List[str]) -> QSelect:
        idx = 1
        columns: List[str] = []
        while idx < len(tokens) and tokens[idx] != "FROM":
            if tokens[idx] != ",":
                columns.append(tokens[idx])
            idx += 1
        idx += 1  # skip FROM
        table = tokens[idx]
        idx += 1
        where = None
        order_by = None
        limit = None
        offset = None
        while idx < len(tokens):
            if tokens[idx] == "WHERE":
                idx += 1
                where = self._parse_where(tokens, idx)
                idx += 3
            elif tokens[idx] == "ORDER":
                idx += 2  # skip BY
                order_by = tokens[idx]
                idx += 1
                if idx < len(tokens) and tokens[idx] in ("ASC", "DESC"):
                    idx += 1
            elif tokens[idx] == "LIMIT":
                idx += 1
                limit = int(tokens[idx])
                idx += 1
            elif tokens[idx] == "OFFSET":
                idx += 1
                offset = int(tokens[idx])
                idx += 1
            else:
                idx += 1
        return QSelect(columns, table, where, order_by, limit, offset)

    def _parse_where(self, tokens: List[str], idx: int) -> QWhere:
        left = tokens[idx]
        op = tokens[idx + 1]
        right = tokens[idx + 2]
        if right.upper() == "TRUE":
            right = True
        elif right.upper() == "FALSE":
            right = False
        elif right.upper() == "NULL":
            right = None
        elif right.startswith("'"):
            right = right.strip("'")
        else:
            try:
                right = int(right)
            except ValueError:
                try:
                    right = float(right)
                except ValueError:
                    pass
        return QWhere(left, op, right)

    def _parse_insert(self, tokens: List[str]) -> QInsert:
        idx = 1
        if tokens[idx] == "INTO":
            idx += 1
        table = tokens[idx]
        idx += 1
        # Simplified: expect "VALUES" then key=value pairs
        values: Dict[str, Any] = {}
        while idx < len(tokens) and tokens[idx] != "VALUES":
            idx += 1
        idx += 1
        # Parse JSON-like object as flat key=value list
        while idx < len(tokens):
            if idx + 2 < len(tokens) and tokens[idx + 1] == "=":
                k = tokens[idx]
                v = tokens[idx + 2]
                if v.startswith("'"):
                    v = v.strip("'")
                else:
                    try:
                        v = int(v)
                    except ValueError:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
                values[k] = v
                idx += 3
            else:
                idx += 1
        return QInsert(table, values)

    def _parse_delete(self, tokens: List[str]) -> QDelete:
        idx = 1
        if tokens[idx] == "FROM":
            idx += 1
        table = tokens[idx]
        idx += 1
        where = None
        if idx < len(tokens) and tokens[idx] == "WHERE":
            idx += 1
            where = self._parse_where(tokens, idx)
        return QDelete(table, where)


# =============================================================================
# Query Planner
# =============================================================================
class QueryPlanner:
    """Simple planner: choose scan vs index, set limits."""

    def plan(self, ast: QSelect) -> Dict[str, Any]:
        plan = {"op": "scan", "table": ast.from_table, "columns": ast.columns, "limit": ast.limit or 10000}
        if ast.where:
            if ast.where.op == "=" and ast.where.left.endswith("_id"):
                plan["op"] = "index_lookup"
                plan["index_field"] = ast.where.left
                plan["index_value"] = ast.where.right
            else:
                plan["filter"] = (ast.where.left, ast.where.op, ast.where.right)
        if ast.order_by:
            plan["sort"] = ast.order_by
        if ast.offset:
            plan["offset"] = ast.offset
        return plan


# =============================================================================
# Execution Engine
# =============================================================================
class ExecutionEngine:
    """Executes plans over in-memory or SQLite-backed tables."""

    OPS = {
        "=": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        ">=": operator.ge,
        "<": operator.lt,
        "<=": operator.le,
    }

    def __init__(self) -> None:
        self._tables: Dict[str, List[Dict[str, Any]]] = {}
        self._indexes: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._lock = threading.RLock()

    def create_table(self, name: str, schema: Optional[List[str]] = None) -> bool:
        with self._lock:
            if name not in self._tables:
                self._tables[name] = []
                self._indexes[name] = {}
                return True
            return False

    def insert(self, table: str, row: Dict[str, Any]) -> bool:
        with self._lock:
            if table not in self._tables:
                self.create_table(table)
            self._tables[table].append(row)
            # Update indexes
            for col, idx in self._indexes.get(table, {}).items():
                if col in row:
                    idx[str(row[col])] = row
            return True

    def execute_plan(self, plan: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        table = plan["table"]
        with self._lock:
            rows = list(self._tables.get(table, []))
        # Index lookup
        if plan.get("op") == "index_lookup":
            field = plan["index_field"]
            val = plan["index_value"]
            idx = self._indexes.get(table, {}).get(field, {})
            if str(val) in idx:
                rows = [idx[str(val)]]
            else:
                rows = [r for r in rows if r.get(field) == val]
        # Filter
        if "filter" in plan:
            field, op_str, val = plan["filter"]
            op_fn = self.OPS.get(op_str, lambda a, b: False)
            rows = [r for r in rows if op_fn(r.get(field), val)]
        # Sort
        if "sort" in plan:
            sort_key = plan["sort"]
            rows = sorted(rows, key=lambda r: r.get(sort_key, 0))
        # Offset / Limit
        offset = plan.get("offset", 0)
        limit = plan.get("limit", len(rows))
        rows = rows[offset:offset + limit]
        return iter(rows)

    def delete(self, table: str, where: Optional[QWhere] = None) -> int:
        with self._lock:
            rows = self._tables.get(table, [])
            if where is None:
                n = len(rows)
                self._tables[table] = []
                return n
            op_fn = self.OPS.get(where.op, lambda a, b: False)
            original = len(rows)
            self._tables[table] = [r for r in rows if not op_fn(r.get(where.left), where.right)]
            return original - len(self._tables[table])

    def create_index(self, table: str, column: str) -> bool:
        with self._lock:
            if table not in self._tables:
                return False
            if table not in self._indexes:
                self._indexes[table] = {}
            idx: Dict[str, Dict[str, Any]] = {}
            for row in self._tables[table]:
                if column in row:
                    idx[str(row[column])] = row
            self._indexes[table][column] = idx
            return True


# =============================================================================
# Table Manager
# =============================================================================
class TableManager:
    """Schema registry and DDL operations."""

    def __init__(self, engine: ExecutionEngine) -> None:
        self.engine = engine
        self._schemas: Dict[str, Dict[str, str]] = {}

    def define(self, name: str, schema: Dict[str, str]) -> bool:
        self._schemas[name] = schema
        return self.engine.create_table(name, list(schema.keys()))

    def get_schema(self, name: str) -> Optional[Dict[str, str]]:
        return self._schemas.get(name)

    def list_tables(self) -> List[str]:
        return list(self._schemas.keys())

    def drop(self, name: str) -> bool:
        if name in self._schemas:
            del self._schemas[name]
            with self.engine._lock:
                self.engine._tables.pop(name, None)
                self.engine._indexes.pop(name, None)
            return True
        return False


# =============================================================================
# Transaction Manager
# =============================================================================
class TransactionManager:
    """Simple BEGIN / COMMIT / ROLLBACK over snapshot copies."""

    def __init__(self, engine: ExecutionEngine) -> None:
        self.engine = engine
        self._snapshots: Dict[str, List[Dict[str, Any]]] = {}
        self._active = False

    def begin(self) -> None:
        with self.engine._lock:
            self._snapshots = {t: list(rows) for t, rows in self.engine._tables.items()}
        self._active = True

    def commit(self) -> None:
        self._snapshots.clear()
        self._active = False

    def rollback(self) -> None:
        with self.engine._lock:
            for t, rows in self._snapshots.items():
                self.engine._tables[t] = rows
        self._snapshots.clear()
        self._active = False


# =============================================================================
# Query Cache
# =============================================================================
class QueryCache:
    """LRU cache for parsed queries + results."""

    def __init__(self, max_size: int = 128) -> None:
        self.max_size = max_size
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry and (time.time() - entry[1]) < 60.0:
                return entry[0]
            return None

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._cache) >= self.max_size:
                oldest = min(self._cache, key=lambda k: self._cache[k][1])
                del self._cache[oldest]
            self._cache[key] = (value, time.time())

    def invalidate(self, table: str) -> None:
        with self._lock:
            to_remove = [k for k in self._cache if f"FROM {table}" in k.upper()]
            for k in to_remove:
                del self._cache[k]


# =============================================================================
# Aggregator
# =============================================================================
class Aggregator:
    """GROUP BY + aggregate functions over result sets."""

    @staticmethod
    def count(rows: Iterator[Dict[str, Any]]) -> int:
        return sum(1 for _ in rows)

    @staticmethod
    def sum(rows: Iterator[Dict[str, Any]], field: str) -> float:
        return sum(r.get(field, 0) for r in rows)

    @staticmethod
    def avg(rows: Iterator[Dict[str, Any]], field: str) -> float:
        vals = [r.get(field, 0) for r in rows]
        return sum(vals) / len(vals) if vals else 0.0

    @staticmethod
    def max(rows: Iterator[Dict[str, Any]], field: str) -> Any:
        return max((r.get(field) for r in rows), default=None)

    @staticmethod
    def min(rows: Iterator[Dict[str, Any]], field: str) -> Any:
        return min((r.get(field) for r in rows), default=None)


# =============================================================================
# Query Kernel Bridge
# =============================================================================
class QueryKernelBridge:
    def __init__(self, engine: ExecutionEngine, event_bus: Any = None) -> None:
        self.engine = engine
        self.bus = event_bus
        self._hooks: List[Callable[[str, Any], None]] = []

    def on_query(self, hook: Callable[[str, Any], None]) -> None:
        self._hooks.append(hook)

    def query(self, sql: str) -> Iterator[Dict[str, Any]]:
        parser = QueryParser()
        ast = parser.parse(sql)
        planner = QueryPlanner()
        plan = planner.plan(ast)
        results = self.engine.execute_plan(plan)
        if self.bus:
            self.bus.publish("query.executed", {"sql": sql})
        for hook in self._hooks:
            hook(sql, plan)
        return results


# =============================================================================
# Main Query Engine
# =============================================================================
class QueryEngine:
    """Top-level query orchestrator."""

    def __init__(self) -> None:
        self.engine = ExecutionEngine()
        self.tables = TableManager(self.engine)
        self.txn = TransactionManager(self.engine)
        self.cache = QueryCache()
        self.bridge = QueryKernelBridge(self.engine)
        self._running = False

    def create_table(self, name: str, schema: Dict[str, str]) -> bool:
        return self.tables.define(name, schema)

    def insert(self, sql: str) -> bool:
        parser = QueryParser()
        ast = parser.parse(sql)
        if isinstance(ast, QInsert):
            return self.engine.insert(ast.into_table, ast.values)
        return False

    def select(self, sql: str) -> List[Dict[str, Any]]:
        cached = self.cache.get(sql)
        if cached is not None:
            return cached
        results = list(self.bridge.query(sql))
        self.cache.put(sql, results)
        return results

    def delete(self, sql: str) -> int:
        parser = QueryParser()
        ast = parser.parse(sql)
        if isinstance(ast, QDelete):
            self.cache.invalidate(ast.from_table)
            return self.engine.delete(ast.from_table, ast.where)
        return 0

    def create_index(self, table: str, column: str) -> bool:
        return self.engine.create_index(table, column)

    def shutdown(self) -> None:
        self._running = False

    def __enter__(self) -> QueryEngine:
        self._running = True
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown()


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Query Engine Demo")
    print("=" * 60)
    qe = QueryEngine()
    qe.create_table("agents", {"agent_id": "TEXT", "name": "TEXT", "role": "TEXT", "score": "INTEGER"})
    qe.insert("INSERT INTO agents VALUES agent_id='a1', name='Alpha', role='trader', score=95")
    qe.insert("INSERT INTO agents VALUES agent_id='a2', name='Beta', role='scanner', score=87")
    qe.insert("INSERT INTO agents VALUES agent_id='a3', name='Gamma', role='trader', score=92")
    qe.create_index("agents", "agent_id")
    res = qe.select("SELECT * FROM agents WHERE role = 'trader' ORDER BY score LIMIT 10")
    print(f"Traders: {res}")
    n = qe.delete("DELETE FROM agents WHERE score < 90")
    print(f"Deleted {n} low-score agents")
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
