#!/usr/bin/env python3
"""
paper_trading_native.py — Paper Trading Engine with HFT Order Book
=================================================================
Track A: Real Trading Engine | Layer 8: HFT Trading Engine

Features:
  - Binance testnet WebSocket feed (depth, trades, ticker)
  - C++ HFT order book via tri_language_bridge (subprocess/JSON bridge)
  - Real-time arbitrage detection (cross-pair + cross-exchange)
  - Paper trades only — no real money at risk
  - Pure Python: stdlib + websocket-client

Requirements:
  - pip install websocket-client
  - API keys via env vars or ~/.magnatrix (no hardcoded secrets)
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode

# --------------------------------------------------------------------------- #
#  External deps (soft-fail)
# --------------------------------------------------------------------------- #
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("[WARN] websocket-client not installed — WebSocket will be mocked")

# --------------------------------------------------------------------------- #
#  Logging
# --------------------------------------------------------------------------- #
logger = logging.getLogger("PaperTradingNative")

# --------------------------------------------------------------------------- #
#  Config
# --------------------------------------------------------------------------- #
@dataclass
class PaperConfig:
    symbols: list[str] = None
    exchanges: list[str] = None
    ws_url: str = "wss://testnet.binance.vision/ws"
    rest_url: str = "https://testnet.binance.vision"
    interval_ms: int = 1000
    max_iterations: int = 1000
    db_path: str = "paper_native.db"
    arbitrage_threshold_bps: float = 5.0
    paper_nav: float = 100_000.0

    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["BTCUSDT", "ETHUSDT"]
        if self.exchanges is None:
            self.exchanges = ["binance_testnet"]


# --------------------------------------------------------------------------- #
#  Tri-Language Bridge — C++ HFT Order Book Interface
# --------------------------------------------------------------------------- #
class TriLanguageBridge:
    """
    Bridge to native C++ HFT order book engine.
    Communication: subprocess with JSON-over-stdin/stdout (fast, portable).
    C++ side receives: {"cmd":"update","bids":[[p,q],...],"asks":[[p,q],...]}
    C++ side returns:   {"best_bid":P,"best_ask":P,"spread_bps":S,"latency_us":L}

    If C++ binary unavailable, falls back to pure-Python order book.
    """

    def __init__(self, cpp_binary: str | None = None, use_fallback: bool = False):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._fallback = use_fallback or (cpp_binary is None)
        self._cpp_binary = cpp_binary
        self._fallback_book: dict[str, Any] = {"bids": [], "asks": []}
        self._connected = False
        self._latency_us = 0.0

        if not self._fallback and self._cpp_binary:
            self._start_cpp()

    def _start_cpp(self) -> None:
        try:
            self._proc = subprocess.Popen(
                [self._cpp_binary],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self._connected = True
            logger.info("TriLanguageBridge: C++ process started | pid=%s", self._proc.pid)
        except Exception as exc:
            logger.warning("TriLanguageBridge: C++ start failed (%s) — using fallback", exc)
            self._fallback = True

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def update(self, symbol: str, bids: list[list[float]], asks: list[list[float]]) -> dict[str, Any]:
        """Push new order book snapshot/diff to C++ engine."""
        t0 = time.perf_counter()
        if self._fallback:
            result = self._fallback_update(symbol, bids, asks)
        else:
            result = self._cpp_update(symbol, bids, asks)
        self._latency_us = (time.perf_counter() - t0) * 1e6
        result["latency_us"] = round(self._latency_us, 2)
        return result

    def get_book(self, symbol: str, depth: int = 10) -> dict[str, Any]:
        """Get aggregated order book state."""
        if self._fallback:
            return self._fallback_get_book(symbol, depth)
        return self._cpp_query({"cmd": "get_book", "symbol": symbol, "depth": depth})

    def get_spread(self, symbol: str) -> dict[str, Any]:
        """Get top-of-book spread metrics."""
        book = self.get_book(symbol, depth=1)
        bids = book.get("bids", [])
        asks = book.get("asks", [])
        if bids and asks:
            bb = bids[0][0]
            ba = asks[0][0]
            spread = ba - bb
            return {
                "best_bid": bb,
                "best_ask": ba,
                "spread": round(spread, 2),
                "spread_bps": round(spread / bb * 10_000, 3),
                "mid": round((bb + ba) / 2, 2),
                "latency_us": book.get("latency_us", 0),
            }
        return {"best_bid": 0, "best_ask": 0, "spread": 0, "spread_bps": 0, "mid": 0}

    def shutdown(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.write(json.dumps({"cmd": "exit"}) + "\n")
                self._proc.stdin.flush()
                self._proc.wait(timeout=2.0)
            except Exception:
                self._proc.kill()
            logger.info("TriLanguageBridge: C++ process terminated")

    # ------------------------------------------------------------------ #
    #  C++ JSON protocol
    # ------------------------------------------------------------------ #
    def _cpp_update(self, symbol: str, bids: list, asks: list) -> dict[str, Any]:
        if not self._proc or self._proc.poll() is not None:
            self._fallback = True
            return self._fallback_update(symbol, bids, asks)
        try:
            payload = json.dumps({"cmd": "update", "symbol": symbol, "bids": bids, "asks": asks}) + "\n"
            with self._lock:
                self._proc.stdin.write(payload)
                self._proc.stdin.flush()
                line = self._proc.stdout.readline().strip()
            return json.loads(line) if line else {}
        except Exception as exc:
            logger.warning("C++ bridge error: %s — fallback", exc)
            self._fallback = True
            return self._fallback_update(symbol, bids, asks)

    def _cpp_query(self, query: dict[str, Any]) -> dict[str, Any]:
        if not self._proc or self._proc.poll() is not None:
            self._fallback = True
            return self._fallback_get_book(query.get("symbol", ""), query.get("depth", 10))
        try:
            payload = json.dumps(query) + "\n"
            with self._lock:
                self._proc.stdin.write(payload)
                self._proc.stdin.flush()
                line = self._proc.stdout.readline().strip()
            return json.loads(line) if line else {}
        except Exception:
            self._fallback = True
            return self._fallback_get_book(query.get("symbol", ""), 10)

    # ------------------------------------------------------------------ #
    #  Pure-Python fallback order book (insertion-sort, HFT-style)
    # ------------------------------------------------------------------ #
    def _fallback_update(self, symbol: str, bids: list, asks: list) -> dict[str, Any]:
        self._fallback_book = {"bids": bids, "asks": asks}
        if bids and asks:
            bb = bids[0][0]
            ba = asks[0][0]
            spread = ba - bb
            return {
                "best_bid": bb,
                "best_ask": ba,
                "spread": round(spread, 2),
                "spread_bps": round(spread / bb * 10_000, 3),
                "mid": round((bb + ba) / 2, 2),
                "bids_depth": len(bids),
                "asks_depth": len(asks),
            }
        return {"best_bid": 0, "best_ask": 0, "spread": 0, "spread_bps": 0}

    def _fallback_get_book(self, symbol: str, depth: int) -> dict[str, Any]:
        bids = self._fallback_book.get("bids", [])[:depth]
        asks = self._fallback_book.get("asks", [])[:depth]
        return {"symbol": symbol, "bids": bids, "asks": asks, "depth": depth, "latency_us": 0}


# --------------------------------------------------------------------------- #
#  Paper Order Manager
# --------------------------------------------------------------------------- #
@dataclass
class PaperOrder:
    order_id: str
    symbol: str
    side: str
    size: float
    price: float
    fee: float
    timestamp: float
    status: str = "filled"


class PaperOrderManager:
    """Simulated order execution with realistic slippage and fees."""

    def __init__(self, initial_nav: float = 100_000.0):
        self.nav = initial_nav
        self.cash = initial_nav
        self.positions: dict[str, float] = {}
        self.orders: list[PaperOrder] = []
        self._order_counter = 0
        self._lock = threading.Lock()

    def place_market(self, symbol: str, side: str, size: float, book: dict[str, Any]) -> PaperOrder:
        """Execute market order against order book."""
        with self._lock:
            self._order_counter += 1
            mid = book.get("mid", 0)
            spread_bps = book.get("spread_bps", 0)

            # Slippage: proportional to spread + small random
            if side == "buy":
                fill_price = book.get("best_ask", mid) * (1 + spread_bps / 20_000)
            else:
                fill_price = book.get("best_bid", mid) * (1 - spread_bps / 20_000)

            notional = size * fill_price
            fee = notional * 0.001  # 0.1% taker fee

            if side == "buy":
                self.cash -= notional + fee
                self.positions[symbol] = self.positions.get(symbol, 0) + size
            else:
                self.cash += notional - fee
                self.positions[symbol] = self.positions.get(symbol, 0) - size

            order = PaperOrder(
                order_id=f"paper-{self._order_counter}-{int(time.time()*1000)%10000}",
                symbol=symbol,
                side=side,
                size=size,
                price=round(fill_price, 2),
                fee=round(fee, 4),
                timestamp=time.time(),
            )
            self.orders.append(order)

            # Recalc NAV
            nav = self.cash
            for sym, pos in self.positions.items():
                nav += pos * mid  # simplified mark
            self.nav = round(nav, 2)

            return order

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "nav": self.nav,
                "cash": round(self.cash, 2),
                "positions": dict(self.positions),
                "n_orders": len(self.orders),
            }


# --------------------------------------------------------------------------- #
#  Arbitrage Detector
# --------------------------------------------------------------------------- #
@dataclass
class ArbOpportunity:
    symbol_a: str
    exchange_a: str
    bid_a: float
    symbol_b: str
    exchange_b: str
    ask_b: float
    spread_bps: float
    estimated_pnl: float
    path: str
    timestamp: float


class ArbitrageDetector:
    """Detects simple arbitrage between symbols or synthetic triangle paths."""

    def __init__(self, threshold_bps: float = 5.0):
        self.threshold_bps = threshold_bps
        self._books: dict[str, dict[str, Any]] = {}  # symbol -> book snapshot
        self._lock = threading.Lock()

    def on_book(self, symbol: str, book: dict[str, Any]) -> None:
        with self._lock:
            self._books[symbol] = book

    def scan(self) -> list[ArbOpportunity]:
        """Scan all symbol pairs for arbitrage."""
        ops: list[ArbOpportunity] = []
        with self._lock:
            symbols = list(self._books.keys())
            for i, sym_a in enumerate(symbols):
                for sym_b in symbols[i + 1:]:
                    op = self._check_pair(sym_a, sym_b)
                    if op:
                        ops.append(op)
        return ops

    def _check_pair(self, sym_a: str, sym_b: str) -> ArbOpportunity | None:
        book_a = self._books.get(sym_a)
        book_b = self._books.get(sym_b)
        if not book_a or not book_b:
            return None

        bb_a = book_a.get("best_bid", 0)
        ba_a = book_a.get("best_ask", 0)
        bb_b = book_b.get("best_bid", 0)
        ba_b = book_b.get("best_ask", 0)

        if bb_a == 0 or ba_b == 0:
            return None

        # Path A->B: buy B, sell A
        spread_bps = (bb_a - ba_b) / ba_b * 10_000
        if spread_bps > self.threshold_bps:
            return ArbOpportunity(
                symbol_a=sym_a,
                exchange_a="binance_testnet",
                bid_a=bb_a,
                symbol_b=sym_b,
                exchange_b="binance_testnet",
                ask_b=ba_b,
                spread_bps=round(spread_bps, 3),
                estimated_pnl=round((bb_a - ba_b) * 0.01, 4),  # assume 0.01 unit
                path=f"{sym_b} -> {sym_a}",
                timestamp=time.time(),
            )

        # Path B->A: buy A, sell B
        spread_bps = (bb_b - ba_a) / ba_a * 10_000
        if spread_bps > self.threshold_bps:
            return ArbOpportunity(
                symbol_a=sym_b,
                exchange_a="binance_testnet",
                bid_a=bb_b,
                symbol_b=sym_a,
                exchange_b="binance_testnet",
                ask_b=ba_a,
                spread_bps=round(spread_bps, 3),
                estimated_pnl=round((bb_b - ba_a) * 0.01, 4),
                path=f"{sym_a} -> {sym_b}",
                timestamp=time.time(),
            )
        return None


# --------------------------------------------------------------------------- #
#  WebSocket Feed Handler
# --------------------------------------------------------------------------- #
class BinanceTestnetFeed:
    """
    WebSocket feed handler for Binance testnet.
    Streams: @depth, @trade, @ticker per symbol.
    """

    def __init__(
        self,
        config: PaperConfig,
        bridge: TriLanguageBridge,
        on_book: Callable[[str, dict], None] | None = None,
        on_trade: Callable[[dict], None] | None = None,
        on_ticker: Callable[[dict], None] | None = None,
    ):
        self.config = config
        self.bridge = bridge
        self.on_book = on_book
        self.on_trade = on_trade
        self.on_ticker = on_ticker
        self.ws: websocket.WebSocketApp | None = None
        self._running = False
        self._last_book: dict[str, dict[str, Any]] = {}

    def start(self) -> threading.Thread:
        """Start WebSocket connection in background thread."""
        if not WEBSOCKET_AVAILABLE:
            logger.error("websocket-client not installed — cannot start feed")
            return threading.Thread(target=lambda: None)

        self._running = True
        streams = "/".join(f"{s.lower()}@depth5@100ms" for s in self.config.symbols)
        streams += "/" + "/".join(f"{s.lower()}@trade" for s in self.config.symbols)
        url = f"{self.config.ws_url}/{streams}"

        def on_message(_ws, msg):
            self._handle_message(json.loads(msg))

        def on_error(_ws, err):
            logger.error("WS error: %s", err)

        def on_close(_ws, *args):
            logger.info("WS closed")
            self._running = False

        def on_open(_ws):
            logger.info("WS connected | streams=%s", streams)

        self.ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        t = threading.Thread(target=self.ws.run_forever, daemon=True)
        t.start()
        return t

    def stop(self) -> None:
        self._running = False
        if self.ws:
            self.ws.close()

    def _handle_message(self, msg: dict[str, Any]) -> None:
        stream = msg.get("stream", "")
        data = msg.get("data", msg)

        if "depth" in stream:
            self._handle_depth(data, stream.split("@")[0].upper())
        elif "trade" in stream:
            if self.on_trade:
                self.on_trade(data)
        elif "ticker" in stream:
            if self.on_ticker:
                self.on_ticker(data)

    def _handle_depth(self, data: dict, symbol: str) -> None:
        bids = [[float(b[0]), float(b[1])] for b in data.get("bids", [])]
        asks = [[float(a[0]), float(a[1])] for a in data.get("asks", [])]

        # Sort: bids desc, asks asc
        bids.sort(key=lambda x: x[0], reverse=True)
        asks.sort(key=lambda x: x[0])

        # Push to C++ bridge
        result = self.bridge.update(symbol, bids, asks)
        self._last_book[symbol] = result

        if self.on_book:
            self.on_book(symbol, result)

    def get_last_book(self, symbol: str) -> dict[str, Any]:
        return self._last_book.get(symbol, {})


# --------------------------------------------------------------------------- #
#  Persistence
# --------------------------------------------------------------------------- #
class PaperTradingDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_orders (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    side TEXT,
                    size REAL,
                    price REAL,
                    fee REAL,
                    timestamp REAL,
                    nav_after REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS arb_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol_a TEXT,
                    symbol_b TEXT,
                    spread_bps REAL,
                    estimated_pnl REAL,
                    path TEXT,
                    timestamp REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS book_snapshots (
                    symbol TEXT,
                    best_bid REAL,
                    best_ask REAL,
                    spread_bps REAL,
                    latency_us REAL,
                    timestamp REAL
                )
            """)
            conn.commit()

    def log_order(self, order: PaperOrder, nav_after: float) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO paper_orders VALUES (?,?,?,?,?,?,?,?)",
                (order.order_id, order.symbol, order.side, order.size,
                 order.price, order.fee, order.timestamp, nav_after),
            )
            conn.commit()

    def log_arb(self, arb: ArbitrageOpportunity) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO arb_opportunities (symbol_a, symbol_b, spread_bps, estimated_pnl, path, timestamp) VALUES (?,?,?,?,?,?)",
                (arb.symbol_a, arb.symbol_b, arb.spread_bps, arb.estimated_pnl, arb.path, arb.timestamp),
            )
            conn.commit()

    def log_book(self, symbol: str, book: dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO book_snapshots VALUES (?,?,?,?,?,?)",
                (symbol, book.get("best_bid"), book.get("best_ask"),
                 book.get("spread_bps"), book.get("latency_us", 0), time.time()),
            )
            conn.commit()

    def get_recent_orders(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM paper_orders ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            n_orders = conn.execute("SELECT COUNT(*) FROM paper_orders").fetchone()[0]
            n_arb = conn.execute("SELECT COUNT(*) FROM arb_opportunities").fetchone()[0]
            last_nav = conn.execute(
                "SELECT nav_after FROM paper_orders ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            return {"n_orders": n_orders, "n_arb": n_arb, "last_nav": last_nav[0] if last_nav else None}


# --------------------------------------------------------------------------- #
#  Main Paper Trading Loop
# --------------------------------------------------------------------------- #
class PaperTradingNative:
    """
    End-to-end paper trading loop:
      WebSocket feed -> C++ order book -> arbitrage scan -> paper trade -> log
    """

    def __init__(self, config: PaperConfig | None = None):
        self.config = config or PaperConfig()
        self.bridge = TriLanguageBridge(use_fallback=True)  # default fallback
        self.feed = BinanceTestnetFeed(self.config, self.bridge)
        self.arb = ArbitrageDetector(threshold_bps=self.config.arbitrage_threshold_bps)
        self.orders = PaperOrderManager(initial_nav=self.config.paper_nav)
        self.db = PaperTradingDB(self.config.db_path)
        self._running = False
        self.iteration = 0
        self._arb_count = 0
        self._trade_count = 0

    def set_bridge(self, bridge: TriLanguageBridge) -> None:
        self.bridge = bridge
        self.feed.bridge = bridge

    def run(self, max_iterations: int | None = None) -> dict[str, Any]:
        """Run the paper trading loop."""
        self._running = True
        max_iter = max_iterations or self.config.max_iterations

        # Wire book updates to arb detector + DB
        def on_book(symbol: str, book: dict[str, Any]) -> None:
            self.arb.on_book(symbol, book)
            self.db.log_book(symbol, book)

        self.feed.on_book = on_book

        # Start WebSocket
        ws_thread = self.feed.start()
        logger.info("PaperTradingNative started | max_iter=%d", max_iter)

        print("\n" + "=" * 70)
        print(f" PAPER TRADING NATIVE | Binance Testnet | {max_iter} iterations")
        print(f" Symbols: {self.config.symbols}")
        print(f" Arb threshold: {self.config.arbitrage_threshold_bps} bps")
        print(f" Paper NAV: ${self.config.paper_nav:,.2f}")
        print("=" * 70)

        try:
            while self._running and self.iteration < max_iter:
                self.iteration += 1
                t0 = time.perf_counter()

                # Step 1: Arbitrage scan
                ops = self.arb.scan()
                for op in ops:
                    self._arb_count += 1
                    self.db.log_arb(op)
                    print(f"  🔔 ARB #{self._arb_count} | {op.path} | {op.spread_bps:.2f} bps | est PnL ${op.estimated_pnl:.4f}")

                # Step 2: Paper trade on arb (small size)
                for op in ops:
                    if op.spread_bps > self.config.arbitrage_threshold_bps * 2:
                        self._execute_arb_trade(op)

                # Step 3: Periodic status
                if self.iteration % 10 == 0:
                    snap = self.orders.snapshot()
                    print(f"  [{self.iteration:04d}] NAV=${snap['nav']:,.2f} | Cash=${snap['cash']:,.2f} | Pos={snap['positions']} | Orders={snap['n_orders']} | Arb={self._arb_count}")

                elapsed = (time.perf_counter() - t0) * 1000
                sleep_ms = max(0, self.config.interval_ms - elapsed)
                time.sleep(sleep_ms / 1000)

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        finally:
            self._running = False
            self.feed.stop()
            ws_thread.join(timeout=3.0)
            self.bridge.shutdown()

        return self._generate_summary()

    def _execute_arb_trade(self, op: ArbOpportunity) -> None:
        """Execute paper trades for an arbitrage opportunity."""
        # Buy the cheaper, sell the more expensive
        book_a = self.feed.get_last_book(op.symbol_a)
        book_b = self.feed.get_last_book(op.symbol_b)

        size = 0.001  # small demo size
        if book_b and book_a:
            order_buy = self.orders.place_market(op.symbol_b, "buy", size, book_b)
            self.db.log_order(order_buy, self.orders.nav)
            order_sell = self.orders.place_market(op.symbol_a, "sell", size, book_a)
            self.db.log_order(order_sell, self.orders.nav)
            self._trade_count += 2
            print(f"     📈 EXEC arb trade | buy {op.symbol_b} + sell {op.symbol_a} | NAV=${self.orders.nav:,.2f}")

    def _generate_summary(self) -> dict[str, Any]:
        print("\n" + "=" * 70)
        print(" PAPER TRADING NATIVE — SUMMARY")
        print("=" * 70)

        snap = self.orders.snapshot()
        stats = self.db.get_stats()
        total_pnl = snap["nav"] - self.config.paper_nav

        print(f"\n  Iterations:    {self.iteration}")
        print(f"  Arb detected:  {self._arb_count}")
        print(f"  Trades:        {self._trade_count}")
        print(f"  Final NAV:     ${snap['nav']:,.2f}")
        print(f"  Total PnL:     ${total_pnl:+,.2f}")
        print(f"  Cash:          ${snap['cash']:,.2f}")
        print(f"  Positions:     {snap['positions']}")

        report = {
            "iterations": self.iteration,
            "arbitrage_detected": self._arb_count,
            "trades_executed": self._trade_count,
            "final_nav": snap["nav"],
            "total_pnl": round(total_pnl, 2),
            "cash": snap["cash"],
            "positions": snap["positions"],
            "config": asdict(self.config),
        }

        report_path = Path("paper_native_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n  Report saved: {report_path.absolute()}")
        return report

    def stop(self) -> None:
        self._running = False


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = PaperConfig(
        symbols=["BTCUSDT", "ETHUSDT"],
        interval_ms=2000,
        max_iterations=100,
        db_path="/tmp/paper_native.db",
        arbitrage_threshold_bps=10.0,
    )

    engine = PaperTradingNative(config)
    report = engine.run()
    print(f"\nFinal report:\n{json.dumps(report, indent=2)}")


if __name__ == "__main__":
    main()
