#!/usr/bin/env python3
"""audit_trail_native.py — MAGNATRIX-OS Trading Layer
Audit Trail & Compliance Logging System.

Pattern: AMATI-PELAJARI-TIRU dari OctagonAI/kalshi-trading-bot-cli (audit trail, trail reader, audit types).

Features:
  - Structured audit trail: every decision, trade, research, risk gate logged
  - Immutable log: append-only, tamper-evident (hash chain)
  - Trail reader: query by time, ticker, action, outcome
  - Compliance report: export for regulatory review
  - Multi-level logging: INFO, DECISION, TRADE, RISK, ERROR
  - Correlation: link related events (research → decision → trade → outcome)

Usage:
    audit = NativeAuditTrail()
    audit.log_decision(ticker="BTC-YES", action="buy", reason="edge=12%, confidence=high")
    audit.log_trade(ticker="BTC-YES", side="yes", contracts=10, price=58, pnl=0)
    audit.log_risk(ticker="BTC-YES", gate="passed", checks=[{"name":"kelly","passed":True}])
    report = audit.compliance_report(start_time, end_time)
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# Data Model
# ═══════════════════════════════════════════════════════════════════════════════

class AuditLevel(Enum):
    INFO = "info"
    DECISION = "decision"
    TRADE = "trade"
    RESEARCH = "research"
    RISK = "risk"
    ERROR = "error"
    SYSTEM = "system"


@dataclass
class AuditEntry:
    id: int
    timestamp: float
    level: str
    ticker: str
    action: str
    reason: str
    data: str          # JSON
    prev_hash: str
    entry_hash: str
    correlation_id: str


# ═══════════════════════════════════════════════════════════════════════════════
# Schema
# ═══════════════════════════════════════════════════════════════════════════════

AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_trail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    level TEXT NOT NULL,
    ticker TEXT,
    action TEXT,
    reason TEXT,
    data TEXT,
    prev_hash TEXT,
    entry_hash TEXT,
    correlation_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_trail(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_ticker ON audit_trail(ticker);
CREATE INDEX IF NOT EXISTS idx_audit_level ON audit_trail(level);
CREATE INDEX IF NOT EXISTS idx_audit_corr ON audit_trail(correlation_id);
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Audit Trail
# ═══════════════════════════════════════════════════════════════════════════════

class NativeAuditTrail:
    """Immutable, tamper-evident audit trail for trading decisions."""

    def __init__(self, db_path: str = "trading/audit_trail.db") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._last_hash = self._get_last_hash()

    def _init_schema(self) -> None:
        self._conn.executescript(AUDIT_SCHEMA)
        self._conn.commit()

    def _get_last_hash(self) -> str:
        row = self._conn.execute(
            "SELECT entry_hash FROM audit_trail ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row["entry_hash"] if row else "0" * 64

    def _compute_hash(self, entry: Dict[str, Any]) -> str:
        content = json.dumps(entry, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def log(self, level: AuditLevel, ticker: str = "", action: str = "",
            reason: str = "", data: Optional[Dict] = None,
            correlation_id: str = "") -> int:
        """Log a single audit entry. Returns entry ID."""
        timestamp = time.time()
        entry_data = {
            "timestamp": timestamp,
            "level": level.value,
            "ticker": ticker,
            "action": action,
            "reason": reason,
            "data": data or {},
            "prev_hash": self._last_hash,
            "correlation_id": correlation_id,
        }
        entry_hash = self._compute_hash(entry_data)

        cursor = self._conn.execute(
            """INSERT INTO audit_trail (timestamp, level, ticker, action, reason, data, prev_hash, entry_hash, correlation_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (timestamp, level.value, ticker, action, reason,
             json.dumps(data or {}), self._last_hash, entry_hash, correlation_id)
        )
        self._conn.commit()
        self._last_hash = entry_hash
        return cursor.lastrowid

    def log_decision(self, ticker: str, action: str, reason: str,
                     data: Optional[Dict] = None, correlation_id: str = "") -> int:
        return self.log(AuditLevel.DECISION, ticker, action, reason, data, correlation_id)

    def log_trade(self, ticker: str, side: str, contracts: int, price: float,
                  pnl: float = 0.0, data: Optional[Dict] = None, correlation_id: str = "") -> int:
        return self.log(AuditLevel.TRADE, ticker, f"{side}:{contracts}@{price}",
                       f"pnl={pnl}", {"side": side, "contracts": contracts, "price": price, "pnl": pnl, **(data or {})}, correlation_id)

    def log_research(self, ticker: str, model_prob: float, market_prob: float,
                     edge: float, data: Optional[Dict] = None, correlation_id: str = "") -> int:
        return self.log(AuditLevel.RESEARCH, ticker, "compute_edge", f"edge={edge:.4f}",
                       {"model_prob": model_prob, "market_prob": market_prob, "edge": edge, **(data or {})}, correlation_id)

    def log_risk(self, ticker: str, gate: str, checks: List[Dict[str, Any]],
                 data: Optional[Dict] = None, correlation_id: str = "") -> int:
        return self.log(AuditLevel.RISK, ticker, f"gate:{gate}", f"checks={len(checks)}",
                       {"checks": checks, **(data or {})}, correlation_id)

    def log_error(self, ticker: str, error: str, data: Optional[Dict] = None, correlation_id: str = "") -> int:
        return self.log(AuditLevel.ERROR, ticker, "error", error, data, correlation_id)

    def query(self, start_time: Optional[float] = None, end_time: Optional[float] = None,
              ticker: Optional[str] = None, level: Optional[str] = None,
              correlation_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        conditions = ["1=1"]
        params = []
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        if ticker:
            conditions.append("ticker = ?")
            params.append(ticker)
        if level:
            conditions.append("level = ?")
            params.append(level)
        if correlation_id:
            conditions.append("correlation_id = ?")
            params.append(correlation_id)

        query = f"SELECT * FROM audit_trail WHERE {' AND '.join(conditions)} ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def verify_integrity(self, limit: int = 1000) -> Tuple[bool, List[str]]:
        """Verify hash chain integrity. Returns (all_ok, list of error messages)."""
        errors = []
        rows = self._conn.execute(
            "SELECT * FROM audit_trail ORDER BY id ASC LIMIT ?", (limit,)
        ).fetchall()
        prev_hash = "0" * 64
        for row in rows:
            entry_data = {
                "timestamp": row["timestamp"], "level": row["level"],
                "ticker": row["ticker"], "action": row["action"],
                "reason": row["reason"], "data": json.loads(row["data"] or "{}"),
                "prev_hash": row["prev_hash"], "correlation_id": row["correlation_id"],
            }
            expected_hash = self._compute_hash(entry_data)
            if row["entry_hash"] != expected_hash:
                errors.append(f"Hash mismatch at id={row['id']}: expected {expected_hash[:16]}..., got {row['entry_hash'][:16]}...")
            if row["prev_hash"] != prev_hash:
                errors.append(f"Chain break at id={row['id']}: prev_hash mismatch")
            prev_hash = row["entry_hash"]
        return len(errors) == 0, errors

    def compliance_report(self, start_time: float, end_time: float) -> Dict[str, Any]:
        entries = self.query(start_time=start_time, end_time=end_time, limit=10000)
        trades = [e for e in entries if e["level"] == "trade"]
        decisions = [e for e in entries if e["level"] == "decision"]
        risks = [e for e in entries if e["level"] == "risk"]
        errors = [e for e in entries if e["level"] == "error"]

        total_pnl = 0.0
        for t in trades:
            try:
                d = json.loads(t["data"] or "{}")
                total_pnl += d.get("pnl", 0)
            except Exception:
                pass

        return {
            "period": (start_time, end_time),
            "total_entries": len(entries),
            "trades": len(trades),
            "decisions": len(decisions),
            "risk_checks": len(risks),
            "errors": len(errors),
            "total_pnl": round(total_pnl, 2),
            "integrity_ok": self.verify_integrity()[0],
        }

    def export_json(self, path: str, start_time: Optional[float] = None, end_time: Optional[float] = None) -> None:
        entries = self.query(start_time=start_time, end_time=end_time, limit=10000)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, default=str)

    def close(self) -> None:
        self._conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    import tempfile, os
    print("=" * 60)
    print("Native Audit Trail — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    db_path = tempfile.mktemp(suffix=".db")
    audit = NativeAuditTrail(db_path)

    # Test 1: Log decision
    print("[Test 1] Log decision")
    id1 = audit.log_decision("BTC-YES", "buy", "edge=12%", {"confidence": "high"}, "corr-001")
    ok = id1 > 0
    print(f"  Decision ID={id1}: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Log trade
    print("[Test 2] Log trade")
    id2 = audit.log_trade("BTC-YES", "yes", 10, 58, 0, correlation_id="corr-001")
    ok2 = id2 > id1
    print(f"  Trade ID={id2} > {id1}: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Query
    print("[Test 3] Query by ticker")
    results = audit.query(ticker="BTC-YES")
    ok3 = len(results) == 2
    print(f"  2 entries for BTC-YES: {ok3} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Query by correlation
    print("[Test 4] Query by correlation_id")
    corr = audit.query(correlation_id="corr-001")
    ok4 = len(corr) == 2
    print(f"  2 entries with corr-001: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Integrity check
    print("[Test 5] Integrity verification")
    ok5, errors = audit.verify_integrity()
    print(f"  Integrity OK: {ok5} (errors={len(errors)}) — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Compliance report
    print("[Test 6] Compliance report")
    report = audit.compliance_report(0, time.time())
    ok6 = report["total_entries"] == 2 and report["trades"] == 1 and report["decisions"] == 1
    print(f"  Report valid: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Export
    print("[Test 7] JSON export")
    json_path = tempfile.mktemp(suffix=".json")
    audit.export_json(json_path)
    ok7 = os.path.exists(json_path) and os.path.getsize(json_path) > 0
    print(f"  JSON exported: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    audit.close()
    os.unlink(db_path)
    os.unlink(json_path)

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
