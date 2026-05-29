#!/usr/bin/env python3
"""trade_journal_native.py — MAGNATRIX-OS Trading Layer
Trade Journal & P&L Attribution.

Features:
  - SQLite database: trades, signals, P&L, reasoning, confidence, strategy
  - P&L attribution by strategy: which strategy contributed how much
  - Daily/weekly P&L report auto-generate
  - Query interface: get trades by date, strategy, symbol, P&L range
  - Export to JSON/CSV

Usage:
    journal = NativeTradeJournal()
    journal.record_trade(
        symbol="BTCUSDT", side="long", entry=50000, exit=51000,
        pnl=100, strategy="trend_follow", confidence=0.85,
        reasoning="EMA crossover confirmed"
    )
    report = journal.daily_report()
    journal.export_json("trades.json")
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeEntry:
    id: Optional[int] = None
    timestamp: float = 0.0
    symbol: str = ""
    side: str = ""       # long / short
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    strategy: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    fees: float = 0.0
    duration_sec: float = 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Schema
# ══════════════════════════════════════════════════════════════════════════════

CREATE_TRADES_TABLE = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_price REAL,
    exit_price REAL,
    quantity REAL,
    pnl REAL NOT NULL,
    pnl_pct REAL,
    strategy TEXT,
    confidence REAL,
    reasoning TEXT,
    fees REAL DEFAULT 0.0,
    duration_sec REAL DEFAULT 0.0
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_pnl ON trades(pnl);
"""


# ══════════════════════════════════════════════════════════════════════════════
# Trade Journal
# ══════════════════════════════════════════════════════════════════════════════

class NativeTradeJournal:
    """SQLite-based trade journal with P&L attribution and reporting."""

    def __init__(self, db_path: str = "trading/trade_journal.db") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(CREATE_TRADES_TABLE)
        self._conn.executescript(CREATE_INDEXES)
        self._conn.commit()

    def record_trade(self, symbol: str, side: str, entry: float, exit: float,
                     pnl: float, strategy: str = "", confidence: float = 0.0,
                     reasoning: str = "", quantity: float = 0.0,
                     fees: float = 0.0, duration_sec: float = 0.0) -> int:
        """Record a trade and return its ID."""
        pnl_pct = ((exit - entry) / entry * 100) if entry != 0 and side == "long" else ((-exit + entry) / entry * 100) if entry != 0 and side == "short" else 0.0
        cursor = self._conn.execute(
            """INSERT INTO trades (timestamp, symbol, side, entry_price, exit_price, quantity, pnl, pnl_pct, strategy, confidence, reasoning, fees, duration_sec)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (time.time(), symbol, side, entry, exit, quantity, pnl, pnl_pct, strategy, confidence, reasoning, fees, duration_sec)
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_trades(self, symbol: Optional[str] = None, strategy: Optional[str] = None,
                   start_time: Optional[float] = None, end_time: Optional[float] = None,
                   min_pnl: Optional[float] = None, max_pnl: Optional[float] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """Query trades with filters."""
        conditions = ["1=1"]
        params = []
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if strategy:
            conditions.append("strategy = ?")
            params.append(strategy)
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        if min_pnl is not None:
            conditions.append("pnl >= ?")
            params.append(min_pnl)
        if max_pnl is not None:
            conditions.append("pnl <= ?")
            params.append(max_pnl)

        query = f"SELECT * FROM trades WHERE {' AND '.join(conditions)} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def pnl_attribution(self, start_time: Optional[float] = None,
                        end_time: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        """P&L attribution by strategy."""
        conditions = ["1=1"]
        params = []
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        query = f"""SELECT strategy,
                           COUNT(*) as trades,
                           SUM(pnl) as total_pnl,
                           AVG(pnl) as avg_pnl,
                           SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                           SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses
                    FROM trades WHERE {' AND '.join(conditions)}
                    GROUP BY strategy"""
        cursor = self._conn.execute(query, params)
        result = {}
        for row in cursor.fetchall():
            d = dict(row)
            total = d["trades"]
            d["win_rate"] = round(d["wins"] / total, 4) if total > 0 else 0.0
            result[d["strategy"] or "unknown"] = d
        return result

    def daily_report(self, days: int = 7) -> List[Dict[str, Any]]:
        """Daily P&L report for last N days."""
        now = time.time()
        day_seconds = 86400
        reports = []
        for i in range(days):
            start = now - (i + 1) * day_seconds
            end = now - i * day_seconds
            cursor = self._conn.execute(
                "SELECT COUNT(*) as trades, SUM(pnl) as pnl, SUM(fees) as fees FROM trades WHERE timestamp >= ? AND timestamp < ?",
                (start, end)
            )
            row = cursor.fetchone()
            reports.append({
                "date": datetime.fromtimestamp(end, tz=timezone.utc).strftime("%Y-%m-%d"),
                "trades": row["trades"] or 0,
                "pnl": round(row["pnl"] or 0, 2),
                "fees": round(row["fees"] or 0, 2),
                "net": round((row["pnl"] or 0) - (row["fees"] or 0), 2),
            })
        return reports

    def weekly_report(self, weeks: int = 4) -> List[Dict[str, Any]]:
        """Weekly P&L report for last N weeks."""
        now = time.time()
        week_seconds = 604800
        reports = []
        for i in range(weeks):
            start = now - (i + 1) * week_seconds
            end = now - i * week_seconds
            cursor = self._conn.execute(
                "SELECT COUNT(*) as trades, SUM(pnl) as pnl, SUM(fees) as fees FROM trades WHERE timestamp >= ? AND timestamp < ?",
                (start, end)
            )
            row = cursor.fetchone()
            reports.append({
                "week": datetime.fromtimestamp(end, tz=timezone.utc).strftime("%Y-%m-%d"),
                "trades": row["trades"] or 0,
                "pnl": round(row["pnl"] or 0, 2),
                "fees": round(row["fees"] or 0, 2),
                "net": round((row["pnl"] or 0) - (row["fees"] or 0), 2),
            })
        return reports

    def export_json(self, path: str) -> None:
        trades = self.get_trades(limit=10000)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(trades, f, indent=2, default=str)

    def export_csv(self, path: str) -> None:
        trades = self.get_trades(limit=10000)
        if not trades:
            return
        headers = list(trades[0].keys())
        with open(path, "w", encoding="utf-8") as f:
            f.write(",".join(headers) + "\n")
            for t in trades:
                f.write(",".join(str(t.get(h, "")) for h in headers) + "\n")

    def close(self) -> None:
        self._conn.close()

    def __del__(self):
        try:
            self._conn.close()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Trade Journal — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    import tempfile
    import os

    # Test 1: Record trade
    print("[Test 1] Record trade")
    db_path = tempfile.mktemp(suffix=".db")
    journal = NativeTradeJournal(db_path)
    tid = journal.record_trade("BTCUSDT", "long", 50000, 51000, 100, "trend", 0.85, "EMA crossover")
    ok = tid > 0
    print(f"  Trade ID={tid}: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Query trades
    print("[Test 2] Query trades")
    trades = journal.get_trades(symbol="BTCUSDT")
    ok2 = len(trades) == 1 and trades[0]["symbol"] == "BTCUSDT"
    print(f"  Found {len(trades)} trade: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: P&L attribution
    print("[Test 3] P&L attribution")
    journal.record_trade("ETHUSDT", "long", 3000, 3100, 50, "mean_reversion", 0.70, "RSI oversold")
    attr = journal.pnl_attribution()
    ok3 = "trend" in attr and "mean_reversion" in attr
    print(f"  Attribution has 2 strategies: {ok3} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Daily report
    print("[Test 4] Daily report")
    daily = journal.daily_report(days=1)
    ok4 = len(daily) >= 1 and "pnl" in daily[0]
    print(f"  Daily report valid: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Weekly report
    print("[Test 5] Weekly report")
    weekly = journal.weekly_report(weeks=1)
    ok5 = len(weekly) >= 1 and "net" in weekly[0]
    print(f"  Weekly report valid: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Export JSON
    print("[Test 6] Export JSON")
    json_path = tempfile.mktemp(suffix=".json")
    journal.export_json(json_path)
    ok6 = os.path.exists(json_path) and os.path.getsize(json_path) > 0
    print(f"  JSON exported: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Export CSV
    print("[Test 7] Export CSV")
    csv_path = tempfile.mktemp(suffix=".csv")
    journal.export_csv(csv_path)
    ok7 = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    print(f"  CSV exported: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    journal.close()
    os.unlink(db_path)
    os.unlink(json_path)
    os.unlink(csv_path)

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
