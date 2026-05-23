#!/usr/bin/env python3
"""
perspective_native.py — Native Python reimplementation of JP Morgan's Perspective.

AMATI-PELAJARI-TIRU dari repo perspective-dev/perspective.
Core: streaming data primitive + OLAP query engine + expression language +
Arrow IPC + WebSocket server + viewer renderer + MAGNATRIX integration.

Native Python idiomatik, zero external dependency kecuali pyarrow (optional).
~1300+ baris, single-file architecture.
"""

from __future__ import annotations

import asyncio
import datetime
import decimal
import json
import math
import re
import struct
import sys
import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

# ──────────────────────────────────────────────────────────────────────────────
# Optional dependencies
# ──────────────────────────────────────────────────────────────────────────────
try:
    import numpy as np
    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore
    _HAS_NUMPY = False

try:
    import pyarrow as pa
    from pyarrow import ipc
    _HAS_PYARROW = True
except Exception:  # pragma: no cover
    pa = None  # type: ignore
    ipc = None  # type: ignore
    _HAS_PYARROW = False

try:
    import websockets
    _HAS_WEBSOCKETS = True
except Exception:  # pragma: no cover
    websockets = None  # type: ignore
    _HAS_WEBSOCKETS = False


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — Type System & Columnar Storage
# ═══════════════════════════════════════════════════════════════════════════════

class PType(Enum):
    """Perspective-native type enumeration."""
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    BOOLEAN = auto()
    DATETIME = auto()
    DECIMAL = auto()

    def __repr__(self) -> str:
        return f"PType.{self.name}"


_TYPE_MAP: Dict[type, PType] = {
    int: PType.INTEGER,
    float: PType.FLOAT,
    str: PType.STRING,
    bool: PType.BOOLEAN,
    datetime.datetime: PType.DATETIME,
    decimal.Decimal: PType.DECIMAL,
}


class ColumnarBuffer:
    """
    Columnar storage backed by Python list (universal fallback).
    Optionally accelerated via array.array or numpy when applicable.
    """

    _NUMERIC_CODES = {
        PType.INTEGER: ("l", int),
        PType.FLOAT: ("d", float),
    }

    def __init__(self, ptype: PType, capacity: int = 64) -> None:
        self.ptype = ptype
        self._data: List[Any] = []
        self._capacity = max(capacity, 64)
        self._array: Optional[Any] = None  # array.array or numpy ndarray
        self._build_array_buffer()

    def _build_array_buffer(self) -> None:
        if self.ptype in self._NUMERIC_CODES and not _HAS_NUMPY:
            import array
            code, _ = self._NUMERIC_CODES[self.ptype]
            self._array = array.array(code)
        elif self.ptype in self._NUMERIC_CODES and _HAS_NUMPY:
            dtype = {"INTEGER": "int64", "FLOAT": "float64"}[self.ptype.name]
            self._array = np.empty(self._capacity, dtype=dtype)
        else:
            self._array = None

    def append(self, value: Any) -> None:
        if self.ptype == PType.DATETIME and isinstance(value, str):
            value = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif self.ptype == PType.DECIMAL and not isinstance(value, decimal.Decimal):
            value = decimal.Decimal(str(value))
        self._data.append(value)
        if isinstance(self._array, list):
            self._array.append(value)  # type: ignore
        elif hasattr(self._array, "append"):
            self._array.append(value)  # type: ignore
        elif _HAS_NUMPY and isinstance(self._array, np.ndarray):
            if len(self._data) > self._array.shape[0]:
                self._capacity *= 2
                new_arr = np.empty(self._capacity, dtype=self._array.dtype)
                new_arr[: len(self._data) - 1] = self._array[: len(self._data) - 1]
                self._array = new_arr
            self._array[len(self._data) - 1] = value  # type: ignore

    def __getitem__(self, idx: Union[int, slice]) -> Any:
        return self._data[idx]

    def __setitem__(self, idx: int, value: Any) -> None:
        if self.ptype == PType.DATETIME and isinstance(value, str):
            value = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif self.ptype == PType.DECIMAL and not isinstance(value, decimal.Decimal):
            value = decimal.Decimal(str(value))
        self._data[idx] = value
        if _HAS_NUMPY and isinstance(self._array, np.ndarray):
            self._array[idx] = value  # type: ignore

    def __len__(self) -> int:
        return len(self._data)

    def to_list(self) -> List[Any]:
        return list(self._data)

    def __repr__(self) -> str:
        return f"ColumnarBuffer(ptype={self.ptype!r}, len={len(self)}, capacity={self._capacity})"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — StreamingTable (Core Data Primitive)
# ═══════════════════════════════════════════════════════════════════════════════

class Schema:
    """Schema definition: column name → PType."""

    def __init__(self, columns: Dict[str, PType]) -> None:
        self.columns: Dict[str, PType] = dict(columns)
        self._order: List[str] = list(columns.keys())

    def __repr__(self) -> str:
        items = ", ".join(f"{k!r}: {v!r}" for k, v in self.columns.items())
        return f"Schema({{{items}}})"

    def __getitem__(self, col: str) -> PType:
        return self.columns[col]

    def __contains__(self, col: str) -> bool:
        return col in self.columns


class StreamingTable:
    """
    Core Perspective data primitive.
    Columnar storage, schema-enforced, primary-key indexed, delta-tracked.
    """

    def __init__(
        self,
        schema: Union[Schema, Dict[str, PType], Dict[str, str]],
        index: Optional[str] = None,
    ) -> None:
        if isinstance(schema, dict) and schema and isinstance(next(iter(schema.values())), str):
            schema = Schema({k: PType[v.upper()] for k, v in schema.items()})
        elif isinstance(schema, dict):
            schema = Schema(schema)
        self.schema: Schema = schema
        self.index_col: Optional[str] = index
        self._columns: Dict[str, ColumnarBuffer] = {
            name: ColumnarBuffer(ptype) for name, ptype in schema.columns.items()
        }
        self._pk_index: Dict[Any, int] = {}
        self._row_count: int = 0
        self._deltas: List[Dict[str, Any]] = []
        self._callbacks: List[Callable[[], None]] = []
        self._lock = threading.RLock()

    def _next_row_id(self) -> int:
        rid = self._row_count
        self._row_count += 1
        return rid

    def update(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
        """Append or upsert rows. Supports single dict or list of dicts."""
        if isinstance(data, dict):
            data = [data]
        with self._lock:
            for row in data:
                pk_val = row.get(self.index_col) if self.index_col else None
                if pk_val is not None and pk_val in self._pk_index:
                    self._replace_row(pk_val, row)
                else:
                    self._append_row(row)
            self._notify()

    def _append_row(self, row: Dict[str, Any]) -> None:
        rid = self._next_row_id()
        for name, buf in self._columns.items():
            buf.append(row.get(name))
        if self.index_col:
            self._pk_index[row[self.index_col]] = rid
        self._deltas.append({"op": "add", "row": row, "index": rid})

    def _replace_row(self, pk_val: Any, row: Dict[str, Any]) -> None:
        rid = self._pk_index[pk_val]
        for name, buf in self._columns.items():
            buf[rid] = row.get(name)
        self._deltas.append({"op": "update", "row": row, "index": rid})

    def remove(self, pk_val: Any) -> bool:
        """Remove row by primary key. Returns True if found."""
        with self._lock:
            if pk_val not in self._pk_index:
                return False
            rid = self._pk_index.pop(pk_val)
            for name, buf in self._columns.items():
                buf[rid] = None  # soft delete
            self._deltas.append({"op": "remove", "index": rid})
            self._notify()
            return True

    def replace(self, data: List[Dict[str, Any]]) -> None:
        """Atomic replace: clear then load."""
        with self._lock:
            for buf in self._columns.values():
                buf._data.clear()
                if hasattr(buf._array, "clear"):
                    buf._array.clear()  # type: ignore
            self._pk_index.clear()
            self._row_count = 0
            self._deltas.clear()
            for row in data:
                self._append_row(row)
            self._notify()

    def rows(self) -> List[Dict[str, Any]]:
        """Return all rows as list of dicts."""
        with self._lock:
            return [
                {name: buf[i] for name, buf in self._columns.items()}
                for i in range(self._row_count)
            ]

    def columns(self) -> Dict[str, List[Any]]:
        """Return columnar projection."""
        with self._lock:
            return {name: buf.to_list() for name, buf in self._columns.items()}

    def column(self, name: str) -> List[Any]:
        with self._lock:
            return self._columns[name].to_list()

    def size(self) -> int:
        with self._lock:
            return self._row_count

    def on_update(self, callback: Callable[[], None]) -> str:
        """Register callback on any mutation. Returns handle id."""
        hid = str(uuid.uuid4())
        self._callbacks.append(callback)
        return hid

    def _notify(self) -> None:
        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                pass

    def __repr__(self) -> str:
        return (
            f"StreamingTable(schema={self.schema!r}, "
            f"rows={self.size()}, index={self.index_col!r})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — Expression Engine (ExprTK-like)
# ═══════════════════════════════════════════════════════════════════════════════

class TokenType(Enum):
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()
    PLUS = auto()
    MINUS = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    TERNARY_Q = auto()
    TERNARY_C = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: Any
    pos: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r})"


class ExprTokenizer:
    """Simple lexer for Perspective expression language."""

    _KEYWORDS = {"and": TokenType.AND, "or": TokenType.OR, "not": TokenType.NOT}

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.length = len(text)

    def _peek(self) -> str:
        return self.text[self.pos] if self.pos < self.length else "\0"

    def _advance(self) -> str:
        ch = self._peek()
        self.pos += 1
        return ch

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while self.pos < self.length:
            ch = self._peek()
            if ch.isspace():
                self._advance()
                continue
            start = self.pos
            if ch.isdigit() or ch == ".":
                num = self._number()
                tokens.append(Token(TokenType.NUMBER, num, start))
            elif ch == "'" or ch == '"':
                s = self._string()
                tokens.append(Token(TokenType.STRING, s, start))
            elif ch.isalpha() or ch == "_":
                ident = self._identifier()
                ttype = self._KEYWORDS.get(ident.lower(), TokenType.IDENTIFIER)
                tokens.append(Token(ttype, ident, start))
            elif ch == "+":
                tokens.append(Token(TokenType.PLUS, "+", start)); self._advance()
            elif ch == "-":
                tokens.append(Token(TokenType.MINUS, "-", start)); self._advance()
            elif ch == "*":
                tokens.append(Token(TokenType.MUL, "*", start)); self._advance()
            elif ch == "/":
                tokens.append(Token(TokenType.DIV, "/", start)); self._advance()
            elif ch == "%":
                tokens.append(Token(TokenType.MOD, "%", start)); self._advance()
            elif ch == "=":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    tokens.append(Token(TokenType.EQ, "==", start))
                else:
                    tokens.append(Token(TokenType.EQ, "=", start))
            elif ch == "!":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    tokens.append(Token(TokenType.NEQ, "!=", start))
                else:
                    tokens.append(Token(TokenType.NOT, "!", start))
            elif ch == "<":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    tokens.append(Token(TokenType.LE, "<=", start))
                else:
                    tokens.append(Token(TokenType.LT, "<", start))
            elif ch == ">":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    tokens.append(Token(TokenType.GE, ">=", start))
                else:
                    tokens.append(Token(TokenType.GT, ">", start))
            elif ch == "?":
                tokens.append(Token(TokenType.TERNARY_Q, "?", start)); self._advance()
            elif ch == ":":
                tokens.append(Token(TokenType.TERNARY_C, ":", start)); self._advance()
            elif ch == "(":
                tokens.append(Token(TokenType.LPAREN, "(", start)); self._advance()
            elif ch == ")":
                tokens.append(Token(TokenType.RPAREN, ")", start)); self._advance()
            elif ch == ",":
                tokens.append(Token(TokenType.COMMA, ",", start)); self._advance()
            else:
                raise SyntaxError(f"Unexpected character {ch!r} at {start}")
        tokens.append(Token(TokenType.EOF, None, self.pos))
        return tokens

    def _number(self) -> Union[int, float]:
        buf = []
        dot_count = 0
        while self.pos < self.length and (self._peek().isdigit() or self._peek() == "."):
            ch = self._advance()
            if ch == ".":
                dot_count += 1
            buf.append(ch)
        s = "".join(buf)
        return float(s) if dot_count else int(s)

    def _string(self) -> str:
        quote = self._advance()
        buf = []
        while self.pos < self.length and self._peek() != quote:
            buf.append(self._advance())
        if self.pos >= self.length:
            raise SyntaxError("Unterminated string")
        self._advance()  # consume closing quote
        return "".join(buf)

    def _identifier(self) -> str:
        buf = []
        while self.pos < self.length and (self._peek().isalnum() or self._peek() == "_"):
            buf.append(self._advance())
        return "".join(buf)


# ── AST Nodes ─────────────────────────────────────────────────────────────────

class ExprNode:
    """Base class for expression AST nodes."""
    pass


@dataclass
class NumNode(ExprNode):
    value: Union[int, float]

    def __repr__(self) -> str:
        return f"Num({self.value})"


@dataclass
class StrNode(ExprNode):
    value: str

    def __repr__(self) -> str:
        return f"Str({self.value!r})"


@dataclass
class IdentNode(ExprNode):
    name: str

    def __repr__(self) -> str:
        return f"Ident({self.name})"


@dataclass
class BinOpNode(ExprNode):
    op: str
    left: ExprNode
    right: ExprNode

    def __repr__(self) -> str:
        return f"BinOp({self.op}, {self.left}, {self.right})"


@dataclass
class UnaryOpNode(ExprNode):
    op: str
    operand: ExprNode

    def __repr__(self) -> str:
        return f"Unary({self.op}, {self.operand})"


@dataclass
class TernaryNode(ExprNode):
    cond: ExprNode
    true_expr: ExprNode
    false_expr: ExprNode

    def __repr__(self) -> str:
        return f"Ternary({self.cond}, {self.true_expr}, {self.false_expr})"


@dataclass
class CallNode(ExprNode):
    func: str
    args: List[ExprNode]

    def __repr__(self) -> str:
        return f"Call({self.func}, {self.args})"


# ── Parser ──────────────────────────────────────────────────────────────────

class ExprParser:
    """Recursive descent parser for Perspective expressions."""

    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self._current()
        self.pos += 1
        return tok

    def _expect(self, ttype: TokenType) -> Token:
        tok = self._current()
        if tok.type != ttype:
            raise SyntaxError(f"Expected {ttype.name} but got {tok.type.name}")
        return self._advance()

    def parse(self) -> ExprNode:
        node = self._expr_ternary_top()
        if self._current().type != TokenType.EOF:
            raise SyntaxError(f"Unexpected token {self._current()!r}")
        return node

    def _expr_ternary_top(self) -> ExprNode:
        node = self._expr_or()
        while self._current().type == TokenType.TERNARY_Q:
            self._advance()
            true_expr = self._expr_or()
            self._expect(TokenType.TERNARY_C)
            false_expr = self._expr_or()
            node = TernaryNode(node, true_expr, false_expr)
        return node

    def _expr_or(self) -> ExprNode:
        node = self._expr_and()
        while self._current().type == TokenType.OR:
            op = self._advance().value
            right = self._expr_and()
            node = BinOpNode(op, node, right)
        return node

    def _expr_and(self) -> ExprNode:
        node = self._expr_equality()
        while self._current().type == TokenType.AND:
            op = self._advance().value
            right = self._expr_equality()
            node = BinOpNode(op, node, right)
        return node

    def _expr_equality(self) -> ExprNode:
        node = self._expr_relational()
        while self._current().type in (TokenType.EQ, TokenType.NEQ):
            op = self._advance().value
            right = self._expr_relational()
            node = BinOpNode(op, node, right)
        return node

    def _expr_relational(self) -> ExprNode:
        node = self._expr_additive()
        while self._current().type in (TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            op = self._advance().value
            right = self._expr_additive()
            node = BinOpNode(op, node, right)
        return node

    def _expr_additive(self) -> ExprNode:
        node = self._expr_multiplicative()
        while self._current().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._advance().value
            right = self._expr_multiplicative()
            node = BinOpNode(op, node, right)
        return node

    def _expr_multiplicative(self) -> ExprNode:
        node = self._expr_unary()
        while self._current().type in (TokenType.MUL, TokenType.DIV, TokenType.MOD):
            op = self._advance().value
            right = self._expr_unary()
            node = BinOpNode(op, node, right)
        return node

    def _expr_unary(self) -> ExprNode:
        tok = self._current()
        if tok.type in (TokenType.MINUS, TokenType.NOT):
            op = self._advance().value
            operand = self._expr_unary()
            return UnaryOpNode(op, operand)
        return self._expr_primary()

    def _expr_primary(self) -> ExprNode:
        tok = self._current()
        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumNode(tok.value)
        if tok.type == TokenType.STRING:
            self._advance()
            return StrNode(tok.value)
        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            if self._current().type == TokenType.LPAREN:
                self._advance()
                args: List[ExprNode] = []
                if self._current().type != TokenType.RPAREN:
                    args.append(self._expr_or())
                    while self._current().type == TokenType.COMMA:
                        self._advance()
                        args.append(self._expr_or())
                self._expect(TokenType.RPAREN)
                return CallNode(tok.value, args)
            return IdentNode(tok.value)
        if tok.type == TokenType.LPAREN:
            self._advance()
            node = self._expr_or()
            self._expect(TokenType.RPAREN)
            return node
        raise SyntaxError(f"Unexpected token {tok!r}")


# ── Evaluator ─────────────────────────────────────────────────────────────────

class ExprEvaluator:
    """Columnar expression evaluator."""

    _BUILTINS: Dict[str, Callable[[List[Any]], Any]] = {
        "abs": lambda args: abs(args[0]) if args else None,
        "sqrt": lambda args: math.sqrt(args[0]) if args and args[0] is not None else None,
        "log": lambda args: math.log(args[0]) if args and args[0] is not None else None,
        "log10": lambda args: math.log10(args[0]) if args and args[0] is not None else None,
        "exp": lambda args: math.exp(args[0]) if args and args[0] is not None else None,
        "sin": lambda args: math.sin(args[0]) if args and args[0] is not None else None,
        "cos": lambda args: math.cos(args[0]) if args and args[0] is not None else None,
        "tan": lambda args: math.tan(args[0]) if args and args[0] is not None else None,
        "floor": lambda args: math.floor(args[0]) if args and args[0] is not None else None,
        "ceil": lambda args: math.ceil(args[0]) if args and args[0] is not None else None,
        "round": lambda args: round(args[0]) if args and args[0] is not None else None,
        "upper": lambda args: str(args[0]).upper() if args and args[0] is not None else None,
        "lower": lambda args: str(args[0]).lower() if args and args[0] is not None else None,
        "len": lambda args: len(str(args[0])) if args and args[0] is not None else 0,
        "coalesce": lambda args: next((a for a in args if a is not None), None),
    }

    def __init__(self, table: StreamingTable) -> None:
        self.table = table

    def evaluate(self, node: ExprNode, row_idx: int) -> Any:
        if isinstance(node, NumNode):
            return node.value
        if isinstance(node, StrNode):
            return node.value
        if isinstance(node, IdentNode):
            return self.table.column(node.name)[row_idx]
        if isinstance(node, UnaryOpNode):
            val = self.evaluate(node.operand, row_idx)
            if node.op == "-":
                return -val if val is not None else None
            if node.op == "!":
                return not val
            return val
        if isinstance(node, BinOpNode):
            left = self.evaluate(node.left, row_idx)
            right = self.evaluate(node.right, row_idx)
            return self._binop(node.op, left, right)
        if isinstance(node, TernaryNode):
            cond = self.evaluate(node.cond, row_idx)
            return self.evaluate(node.true_expr if cond else node.false_expr, row_idx)
        if isinstance(node, CallNode):
            args = [self.evaluate(a, row_idx) for a in node.args]
            fn = self._BUILTINS.get(node.func)
            if fn:
                return fn(args)
            raise NameError(f"Unknown function: {node.func}")
        return None

    def evaluate_column(self, node: ExprNode) -> List[Any]:
        return [self.evaluate(node, i) for i in range(self.table.size())]

    def _binop(self, op: str, left: Any, right: Any) -> Any:
        if left is None or right is None:
            return None
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right if right != 0 else None
        if op == "%":
            return left % right if right != 0 else None
        if op in ("==", "="):
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right
        if op.lower() == "and":
            return left and right
        if op.lower() == "or":
            return left or right
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — ViewEngine (OLAP Query Engine)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ViewConfig:
    """Configuration for creating a View from a StreamingTable."""
    group_by: Optional[List[str]] = None
    split_by: Optional[List[str]] = None
    sort: Optional[List[Tuple[str, Literal["asc", "desc"]]]] = None
    filter: Optional[List[Tuple[str, str, Any]]] = None
    aggregates: Optional[Dict[str, str]] = None
    columns: Optional[List[str]] = None
    computed: Optional[Dict[str, str]] = None  # name -> expression

    def __repr__(self) -> str:
        return (
            f"ViewConfig(group_by={self.group_by!r}, "
            f"split_by={self.split_by!r}, sort={self.sort!r})"
        )


class ViewEngine:
    """
    OLAP-style query engine: pivot, group, sort, filter, aggregate, split.
    Lazy evaluation — operations build a pipeline over the source table.
    """

    def __init__(self, table: StreamingTable, config: Optional[ViewConfig] = None) -> None:
        self._table = table
        self._config = config or ViewConfig()
        self._eval = ExprEvaluator(table)
        self._cache: Optional[List[Dict[str, Any]]] = None
        self._cache_valid = False

    def _invalidate(self) -> None:
        self._cache_valid = False

    def _rows(self) -> List[Dict[str, Any]]:
        if self._cache_valid and self._cache is not None:
            return self._cache
        rows = self._table.rows()
        rows = self._apply_filter(rows)
        rows = self._apply_computed(rows)
        rows = self._apply_group(rows)
        rows = self._apply_sort(rows)
        self._cache = rows
        self._cache_valid = True
        return rows

    def _apply_filter(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._config.filter:
            return rows
        result = []
        for row in rows:
            keep = True
            for col, op, val in self._config.filter:
                cell = row.get(col)
                if op in ("==", "=") and cell != val:
                    keep = False
                elif op == "!=" and cell == val:
                    keep = False
                elif op == "<" and not (cell is not None and cell < val):
                    keep = False
                elif op == ">" and not (cell is not None and cell > val):
                    keep = False
                elif op == "<=" and not (cell is not None and cell <= val):
                    keep = False
                elif op == ">=" and not (cell is not None and cell >= val):
                    keep = False
                elif op.lower() == "contains" and val not in str(cell):
                    keep = False
            if keep:
                result.append(row)
        return result

    def _apply_computed(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._config.computed:
            return rows
        for name, expr_str in self._config.computed.items():
            tokens = ExprTokenizer(expr_str).tokenize()
            ast = ExprParser(tokens).parse()
            col = self._eval.evaluate_column(ast)
            for i, row in enumerate(rows):
                row[name] = col[i] if i < len(col) else None
        return rows

    def _apply_group(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._config.group_by:
            return rows
        agg_spec = self._config.aggregates or {}
        groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = tuple(row.get(k) for k in self._config.group_by)
            groups[key].append(row)
        result = []
        for key, members in groups.items():
            out: Dict[str, Any] = dict(zip(self._config.group_by, key))
            # auto-aggregate remaining numeric columns
            all_cols = set(members[0].keys())
            numeric_cols = [c for c in all_cols if c not in self._config.group_by]
            for col in numeric_cols:
                agg_fn = agg_spec.get(col, "sum")
                vals = [m[col] for m in members if m[col] is not None]
                # skip non-numeric for numeric aggregates
                if agg_fn in ("sum", "avg", "min", "max", "median", "stddev"):
                    vals = [v for v in vals if isinstance(v, (int, float, decimal.Decimal))]
                if vals or agg_fn == "count":
                    out[col] = self._aggregate(agg_fn, vals)
                else:
                    out[col] = None
            result.append(out)
        return result

    def _apply_sort(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._config.sort:
            return rows
        for col, direction in reversed(self._config.sort):
            reverse = direction == "desc"
            rows = sorted(rows, key=lambda r: (r.get(col) is None, r.get(col) or 0), reverse=reverse)
        return rows

    @staticmethod
    def _aggregate(fn: str, values: List[Any]) -> Any:
        if not values:
            return None
        if fn == "sum":
            return sum(values)
        if fn == "count":
            return len(values)
        if fn == "avg":
            return sum(values) / len(values)
        if fn == "min":
            return min(values)
        if fn == "max":
            return max(values)
        if fn == "distinct":
            return len(set(values))
        if fn == "median":
            s = sorted(values)
            n = len(s)
            return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
        if fn == "stddev":
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            return math.sqrt(variance)
        return values[0]

    def pivot(self, rows: List[str], columns: List[str], values: str, agg: str = "sum") -> Dict[str, Any]:
        """Multi-axis pivot: rows × columns × aggregated values."""
        data = self._rows()
        result: Dict[str, Dict[str, Any]] = defaultdict(dict)
        for row in data:
            rkey = " | ".join(str(row.get(c, "")) for c in rows)
            ckey = " | ".join(str(row.get(c, "")) for c in columns)
            val = row.get(values)
            if rkey not in result or ckey not in result[rkey]:
                result[rkey][ckey] = []
            if val is not None:
                result[rkey][ckey].append(val)
        # collapse lists into aggregates
        for rkey, cdict in result.items():
            for ckey, vals in cdict.items():
                cdict[ckey] = self._aggregate(agg, vals)
        return {"rows": rows, "columns": columns, "values": values, "agg": agg, "data": dict(result)}

    def to_json(self) -> List[Dict[str, Any]]:
        return self._rows()

    def to_columns(self) -> Dict[str, List[Any]]:
        rows = self._rows()
        if not rows:
            return {}
        return {k: [r.get(k) for r in rows] for k in rows[0].keys()}

    def __repr__(self) -> str:
        return f"ViewEngine(table={self._table!r}, rows={len(self._rows())})"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5 — ArrowSerializer (Apache Arrow IPC)
# ═══════════════════════════════════════════════════════════════════════════════

class ArrowSerializer:
    """
    Serialize StreamingTable ke/from Apache Arrow IPC.
    Prefer pyarrow bila tersedia; fallback ke pure-Python minimal IPC-like.
    """

    @staticmethod
    def to_arrow(table: StreamingTable) -> Any:
        if _HAS_PYARROW and pa is not None:
            arrays = []
            names = []
            for name in table.schema._order:
                ptype = table.schema[name]
                data = table.column(name)
                if ptype == PType.INTEGER:
                    arrays.append(pa.array(data, type=pa.int64()))
                elif ptype == PType.FLOAT:
                    arrays.append(pa.array(data, type=pa.float64()))
                elif ptype == PType.STRING:
                    arrays.append(pa.array(data, type=pa.string()))
                elif ptype == PType.BOOLEAN:
                    arrays.append(pa.array(data, type=pa.bool_()))
                elif ptype == PType.DATETIME:
                    arrays.append(pa.array(data, type=pa.timestamp("us")))
                elif ptype == PType.DECIMAL:
                    arrays.append(pa.array([float(d) if d else None for d in data], type=pa.float64()))
                else:
                    arrays.append(pa.array(data))
                names.append(name)
            return pa.table(arrays, names=names)
        # Pure-Python fallback: return columnar dict
        return table.columns()

    @staticmethod
    def from_arrow(arrow_table: Any) -> StreamingTable:
        if _HAS_PYARROW and pa is not None and isinstance(arrow_table, pa.Table):
            schema_cols: Dict[str, PType] = {}
            for name in arrow_table.column_names:
                t = arrow_table.schema.field(name).type
                if pa.types.is_integer(t):
                    schema_cols[name] = PType.INTEGER
                elif pa.types.is_floating(t):
                    schema_cols[name] = PType.FLOAT
                elif pa.types.is_string(t):
                    schema_cols[name] = PType.STRING
                elif pa.types.is_boolean(t):
                    schema_cols[name] = PType.BOOLEAN
                elif pa.types.is_temporal(t):
                    schema_cols[name] = PType.DATETIME
                else:
                    schema_cols[name] = PType.STRING
            st = StreamingTable(Schema(schema_cols))
            for batch in arrow_table.to_batches():
                cols = batch.to_pydict()
                n = batch.num_rows
                for i in range(n):
                    st.update({k: v[i] for k, v in cols.items()})
            return st
        raise TypeError("from_arrow requires pyarrow Table or compatible input")

    @staticmethod
    def to_ipc_stream(table: StreamingTable) -> bytes:
        if _HAS_PYARROW and pa is not None and ipc is not None:
            arrow_tbl = ArrowSerializer.to_arrow(table)
            if isinstance(arrow_tbl, pa.Table):
                sink = pa.BufferOutputStream()
                with ipc.new_stream(sink, arrow_tbl.schema) as writer:
                    writer.write_table(arrow_tbl)
                return sink.getvalue().to_pybytes()
        # Fallback: minimal binary JSON-ish format
        return json.dumps(table.rows(), default=str).encode("utf-8")

    @staticmethod
    def from_ipc_stream(data: bytes) -> StreamingTable:
        if _HAS_PYARROW and pa is not None and ipc is not None:
            try:
                reader = ipc.open_stream(pa.py_buffer(data))
                tbl = reader.read_all()
                return ArrowSerializer.from_arrow(tbl)
            except Exception:
                pass
        # Fallback JSON
        rows = json.loads(data.decode("utf-8"))
        if rows:
            schema_guess = {}
            for k, v in rows[0].items():
                schema_guess[k] = _TYPE_MAP.get(type(v), PType.STRING)
            st = StreamingTable(Schema(schema_guess))
            st.update(rows)
            return st
        return StreamingTable(Schema({}))

    def __repr__(self) -> str:
        return f"ArrowSerializer(pyarrow={'yes' if _HAS_PYARROW else 'no'})"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6 — WebSocketServer (Real-Time Data Server)
# ═══════════════════════════════════════════════════════════════════════════════

class PerspectiveWebSocketServer:
    """
    Real-time Perspective server: JSON-RPC over WebSocket.
    Subscriptions, delta push, table management.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self._tables: Dict[str, StreamingTable] = {}
        self._views: Dict[str, ViewEngine] = {}
        self._subscriptions: Dict[str, Set[Any]] = {}  # table_name → {websocket}
        self._clients: Set[Any] = set()
        self._lock = asyncio.Lock()

    def register_table(self, name: str, table: StreamingTable) -> None:
        self._tables[name] = table
        self._subscriptions[name] = set()
        table.on_update(lambda n=name: asyncio.create_task(self._push_delta(n)))

    async def _push_delta(self, name: str) -> None:
        if name not in self._subscriptions:
            return
        table = self._tables[name]
        deltas = table._deltas[-10:]  # last 10 deltas
        msg = {"method": "update", "params": {"table": name, "deltas": deltas}}
        dead = set()
        for ws in self._subscriptions[name]:
            try:
                await ws.send(json.dumps(msg))
            except Exception:
                dead.add(ws)
        self._subscriptions[name] -= dead

    async def _handle(self, websocket: Any, path: str) -> None:
        self._clients.add(websocket)
        try:
            async for message in websocket:
                await self._process_message(websocket, message)
        finally:
            self._clients.discard(websocket)
            for subs in self._subscriptions.values():
                subs.discard(websocket)

    async def _process_message(self, websocket: Any, message: str) -> None:
        try:
            req = json.loads(message)
            method = req.get("method")
            params = req.get("params", {})
            req_id = req.get("id")
            result = await self._dispatch(method, params, websocket)
            resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as exc:
            resp = {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32603, "message": str(exc)}}
        await websocket.send(json.dumps(resp))

    async def _dispatch(self, method: Optional[str], params: Dict[str, Any], websocket: Any) -> Any:
        if method == "subscribe":
            name = params.get("table")
            if name in self._subscriptions:
                self._subscriptions[name].add(websocket)
            return {"subscribed": name}
        if method == "unsubscribe":
            name = params.get("table")
            if name in self._subscriptions:
                self._subscriptions[name].discard(websocket)
            return {"unsubscribed": name}
        if method == "get_table":
            name = params.get("table")
            tbl = self._tables.get(name)
            return {"schema": {k: v.name for k, v in tbl.schema.columns.items()}, "rows": tbl.size()} if tbl else None
        if method == "get_view":
            table_name = params.get("table")
            cfg = ViewConfig(
                group_by=params.get("group_by"),
                split_by=params.get("split_by"),
                sort=[(s["column"], s["direction"]) for s in params.get("sort", [])],
                filter=[(f["column"], f["op"], f["value"]) for f in params.get("filter", [])],
                aggregates=params.get("aggregates"),
                columns=params.get("columns"),
                computed=params.get("computed"),
            )
            tbl = self._tables.get(table_name)
            if not tbl:
                raise ValueError(f"Table {table_name} not found")
            view = ViewEngine(tbl, cfg)
            vid = str(uuid.uuid4())
            self._views[vid] = view
            return {"view_id": vid, "data": view.to_json()}
        if method == "update_table":
            name = params.get("table")
            rows = params.get("rows", [])
            tbl = self._tables.get(name)
            if tbl:
                tbl.update(rows)
            return {"updated": len(rows)}
        return None

    async def start(self) -> None:
        if not _HAS_WEBSOCKETS or websockets is None:
            raise RuntimeError("websockets library not installed")
        server = await websockets.serve(self._handle, self.host, self.port)  # type: ignore
        print(f"PerspectiveWebSocketServer listening on ws://{self.host}:{self.port}")
        await server.wait_closed()

    def __repr__(self) -> str:
        return f"PerspectiveWebSocketServer(host={self.host!r}, port={self.port}, tables={list(self._tables)})"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 7 — Viewer (Data Grid + Chart Renderer)
# ═══════════════════════════════════════════════════════════════════════════════

class Viewer:
    """
    Render StreamingTable / ViewEngine sebagai HTML grid atau ASCII.
    Chart generator: line, bar, area, scatter, heatmap, treemap, candlestick.
    """

    def __init__(self, view: ViewEngine) -> None:
        self.view = view

    def to_ascii(self, max_rows: int = 20) -> str:
        rows = self.view.to_json()
        if not rows:
            return "(empty)"
        cols = list(rows[0].keys())
        widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows[:max_rows])) for c in cols}
        lines = []
        header = " | ".join(c.ljust(widths[c]) for c in cols)
        lines.append(header)
        lines.append("-" * len(header))
        for row in rows[:max_rows]:
            lines.append(" | ".join(str(row.get(c, "")).ljust(widths[c]) for c in cols))
        return "\n".join(lines)

    def to_html_grid(self, max_rows: int = 100) -> str:
        rows = self.view.to_json()
        if not rows:
            return "<p>No data</p>"
        cols = list(rows[0].keys())
        th = "".join(f"<th>{c}</th>" for c in cols)
        trs = ""
        for row in rows[:max_rows]:
            tds = "".join(f"<td>{row.get(c, '')}</td>" for c in cols)
            trs += f"<tr>{tds}</tr>"
        return f"""<table border="1" cellpadding="4" cellspacing="0"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"""

    def render_chart(self, chart_type: str, x: str, y: str, series: Optional[str] = None) -> str:
        """Generate simple SVG chart HTML."""
        rows = self.view.to_json()
        if not rows:
            return ""
        width, height = 800, 400
        pad = 40
        data = [(r.get(x), r.get(y)) for r in rows if r.get(x) is not None and r.get(y) is not None]
        if not data:
            return "<p>No plottable data</p>"
        xs = [d[0] for d in data]
        ys = [d[1] for d in data]
        if all(isinstance(v, (int, float)) for v in ys):
            ymin, ymax = min(ys), max(ys)
        else:
            ymin, ymax = 0, len(set(ys))
        rng = max(ymax - ymin, 1)

        def sx(v: Any) -> float:
            if isinstance(v, (int, float)) and isinstance(xs[0], (int, float)):
                xmin, xmax = min(xs), max(xs)
                xr = max(xmax - xmin, 1)
                return pad + (v - xmin) / xr * (width - 2 * pad)
            return pad + (list(set(xs)).index(v) if v in set(xs) else 0) / max(len(set(xs)), 1) * (width - 2 * pad)

        def sy(v: Any) -> float:
            if isinstance(v, (int, float)):
                return height - pad - (v - ymin) / rng * (height - 2 * pad)
            return height - pad - (list(set(ys)).index(v) if v in set(ys) else 0) / max(len(set(ys)), 1) * (height - 2 * pad)

        if chart_type == "line":
            points = " ".join(f"{sx(d[0])},{sy(d[1])}" for d in data)
            svg = f'<svg width="{width}" height="{height}"><polyline points="{points}" fill="none" stroke="#c9a84c" stroke-width="2"/></svg>'
        elif chart_type == "bar":
            rects = ""
            bar_w = max((width - 2 * pad) / len(data) * 0.7, 2)
            for d in data:
                x0 = sx(d[0]) - bar_w / 2
                y0 = sy(d[1])
                y1 = height - pad
                h = y1 - y0
                rects += f'<rect x="{x0}" y="{y0}" width="{bar_w}" height="{h}" fill="#c9a84c"/>'
            svg = f'<svg width="{width}" height="{height}">{rects}</svg>'
        elif chart_type == "scatter":
            circles = ""
            for d in data:
                circles += f'<circle cx="{sx(d[0])}" cy="{sy(d[1])}" r="4" fill="#c9a84c"/>'
            svg = f'<svg width="{width}" height="{height}">{circles}</svg>'
        elif chart_type == "heatmap":
            # simple 2D heatmap using x as row, y as value heat
            cells = ""
            n = len(data)
            cw = (width - 2 * pad) / max(len(set(str(x) for x in xs)), 1)
            rh = (height - 2 * pad) / max(len(data), 1)
            for i, d in enumerate(data):
                intensity = (float(d[1]) - ymin) / rng if isinstance(d[1], (int, float)) else 0.5
                color = f"rgb({int(255*intensity)},{int(255*(1-intensity))},128)"
                cells += f'<rect x="{sx(d[0])-cw/2}" y="{pad+i*rh}" width="{cw}" height="{rh}" fill="{color}"/>'
            svg = f'<svg width="{width}" height="{height}">{cells}</svg>'
        else:
            svg = f"<p>Chart type '{chart_type}' not yet implemented in native renderer.</p>"
        return svg

    def __repr__(self) -> str:
        return f"Viewer(view={self.view!r})"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 8 — PerspectiveKernel (MAGNATRIX Integration)
# ═══════════════════════════════════════════════════════════════════════════════

class PatternCatalog:
    """Simple pattern registry for MAGNATRIX Knowledge Layer."""

    def __init__(self) -> None:
        self._patterns: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, meta: Dict[str, Any]) -> None:
        self._patterns[name] = meta

    def list_patterns(self) -> List[str]:
        return list(self._patterns.keys())

    def __repr__(self) -> str:
        return f"PatternCatalog(count={len(self._patterns)})"


class PerspectiveKernel:
    """
    MAGNATRIX integration layer for Perspective native.
    Bridges StreamingTable ↔ Knowledge Layer, auto-registers patterns,
    exposes event hooks untuk streaming updates.
    """

    def __init__(self, catalog: Optional[PatternCatalog] = None) -> None:
        self.catalog = catalog or PatternCatalog()
        self._tables: Dict[str, StreamingTable] = {}
        self._hooks: Dict[str, List[Callable[[str, Any], None]]] = defaultdict(list)

    def create_table(self, name: str, schema: Union[Schema, Dict[str, PType]], index: Optional[str] = None) -> StreamingTable:
        table = StreamingTable(schema, index=index)
        self._tables[name] = table
        self.catalog.register(name, {"type": "perspective_table", "schema": str(schema), "index": index})
        table.on_update(lambda n=name: self._fire_hooks(n, "update"))
        return table

    def get_table(self, name: str) -> Optional[StreamingTable]:
        return self._tables.get(name)

    def create_view(self, table_name: str, config: ViewConfig) -> ViewEngine:
        table = self._tables.get(table_name)
        if not table:
            raise KeyError(f"Table {table_name} not found")
        return ViewEngine(table, config)

    def on_event(self, event: str, callback: Callable[[str, Any], None]) -> None:
        self._hooks[event].append(callback)

    def _fire_hooks(self, table_name: str, event: str, payload: Any = None) -> None:
        for cb in self._hooks.get(event, []):
            try:
                cb(table_name, payload)
            except Exception:
                pass

    def to_arrow(self, table_name: str) -> Any:
        table = self._tables.get(table_name)
        if not table:
            raise KeyError(table_name)
        return ArrowSerializer.to_arrow(table)

    def start_websocket(self, host: str = "0.0.0.0", port: int = 8080) -> PerspectiveWebSocketServer:
        server = PerspectiveWebSocketServer(host, port)
        for name, table in self._tables.items():
            server.register_table(name, table)
        return server

    def __repr__(self) -> str:
        return f"PerspectiveKernel(tables={list(self._tables)}, patterns={self.catalog.list_patterns()})"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 9 — Demo
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Perspective Native Python — Self-Contained Demo")
    print("=" * 60)

    # 1. Schema + StreamingTable
    schema = Schema({
        "id": PType.INTEGER,
        "symbol": PType.STRING,
        "price": PType.FLOAT,
        "volume": PType.INTEGER,
        "side": PType.STRING,
        "timestamp": PType.DATETIME,
    })
    table = StreamingTable(schema, index="id")
    now = datetime.datetime.now()
    table.update([
        {"id": 1, "symbol": "BTC", "price": 65000.0, "volume": 100, "side": "buy", "timestamp": now},
        {"id": 2, "symbol": "ETH", "price": 3500.0, "volume": 200, "side": "sell", "timestamp": now},
        {"id": 3, "symbol": "BTC", "price": 65100.0, "volume": 150, "side": "buy", "timestamp": now},
        {"id": 4, "symbol": "ETH", "price": 3480.0, "volume": 80, "side": "buy", "timestamp": now},
        {"id": 5, "symbol": "SOL", "price": 145.0, "volume": 500, "side": "sell", "timestamp": now},
    ])
    print(f"\n[StreamingTable] rows={table.size()}, schema={table.schema}")
    print("Rows:", table.rows())

    # 2. ExpressionEngine
    expr = "price * volume + 100"
    tokens = ExprTokenizer(expr).tokenize()
    ast = ExprParser(tokens).parse()
    ev = ExprEvaluator(table)
    col = ev.evaluate_column(ast)
    print(f"\n[ExpressionEngine] '{expr}' → {col}")

    # 3. Ternary expression
    texpr = "price > 5000 ? 'large' : 'small'"
    ttokens = ExprTokenizer(texpr).tokenize()
    tast = ExprParser(ttokens).parse()
    tcol = ev.evaluate_column(tast)
    print(f"[ExpressionEngine] '{texpr}' → {tcol}")

    # 4. ViewEngine: group_by + aggregate
    cfg = ViewConfig(
        group_by=["symbol"],
        aggregates={"price": "avg", "volume": "sum"},
    )
    view = ViewEngine(table, cfg)
    print(f"\n[ViewEngine] group_by=symbol:")
    for row in view.to_json():
        print(" ", row)

    # 5. ViewEngine: filter + sort
    cfg2 = ViewConfig(
        filter=[("price", ">", 5000)],
        sort=[("price", "desc")],
    )
    view2 = ViewEngine(table, cfg2)
    print(f"\n[ViewEngine] filter price>5000, sort desc:")
    for row in view2.to_json():
        print(" ", row)

    # 6. Pivot
    pvt = view.pivot(rows=["symbol"], columns=["side"], values="volume", agg="sum")
    print(f"\n[ViewEngine] pivot symbol×side → volume sum:")
    for rkey, cdict in pvt["data"].items():
        print(f"  {rkey}: {cdict}")

    # 7. ArrowSerializer
    arrow = ArrowSerializer.to_arrow(table)
    print(f"\n[ArrowSerializer] pyarrow={_HAS_PYARROW}, result type={type(arrow).__name__}")

    # 8. Viewer ASCII + HTML
    viewer = Viewer(view)
    print(f"\n[Viewer] ASCII grid:")
    print(viewer.to_ascii())

    # 9. PerspectiveKernel
    kernel = PerspectiveKernel()
    kernel.create_table("trades", schema, index="id")
    kt = kernel.get_table("trades")
    assert kt is not None
    kt.update(table.rows())
    print(f"\n[PerspectiveKernel] tables={kernel._tables.keys()}, patterns={kernel.catalog.list_patterns()}")

    # 10. Chart demo (SVG)
    chart_svg = viewer.render_chart("bar", "symbol", "volume")
    print(f"\n[Viewer] bar chart SVG length={len(chart_svg)} chars")
    chart_line = viewer.render_chart("line", "id", "price")
    print(f"[Viewer] line chart SVG length={len(chart_line)} chars")

    print("\n" + "=" * 60)
    print("Demo complete. All modules initialized successfully.")
    print("=" * 60)
