#!/usr/bin/env python3
"""Market Data Recorder for MAGNATRIX-OS."""
from __future__ import annotations
import json, os, sqlite3, time
from typing import Any, Dict, List, Optional

class MarketDataRecorder:
    def __init__(self, repo_root="", db_path="data/market.db"):
        self.repo_root = repo_root
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_tables()
    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ticks (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                price REAL,
                volume REAL,
                timestamp REAL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS klines (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                timestamp REAL
            )
        """)
        self.conn.commit()
    def record_tick(self, symbol: str, price: float, volume: float):
        self.conn.execute("INSERT INTO ticks (symbol, price, volume, timestamp) VALUES (?, ?, ?, ?)",
                         (symbol, price, volume, time.time()))
        self.conn.commit()
    def record_kline(self, symbol: str, o: float, h: float, l: float, c: float, v: float):
        self.conn.execute("INSERT INTO klines (symbol, open, high, low, close, volume, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (symbol, o, h, l, c, v, time.time()))
        self.conn.commit()
    def query_ticks(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM ticks WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?", (symbol, limit))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    def to_dict(self): return {"db": self.db_path}
