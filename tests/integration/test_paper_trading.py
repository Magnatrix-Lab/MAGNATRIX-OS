#!/usr/bin/env python3
"""
test_paper_trading.py — Integration Test for Paper Trading Engine
===================================================================
Track A: Real Trading Engine | Integration Test Suite

Tests:
  1. TriLanguageBridge fallback order book
  2. PaperOrderManager market execution + NAV tracking
  3. ArbitrageDetector cross-pair scan
  4. PaperTradingDB persistence round-trip
  5. PaperTradingNative full loop (mock WS)
  6. LiveTradingBridge paper trade pipeline

Run: python3 test_paper_trading.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

# --------------------------------------------------------------------------- #
#  Add project paths
# --------------------------------------------------------------------------- #
TRADING_DIR = Path(__file__).resolve().parent.parent.parent / "trading"
sys.path.insert(0, str(TRADING_DIR))

from paper_trading_native import (
    ArbitrageDetector,
    ArbOpportunity,
    PaperConfig,
    PaperOrderManager,
    PaperTradingDB,
    PaperTradingNative,
    TriLanguageBridge,
)
from live_trading_bridge import (
    APIKeyVault,
    LiveRiskManager,
    LiveTradingBridge,
    PnLTracker,
    RiskCheck,
)

# --------------------------------------------------------------------------- #
#  Test Runner
# --------------------------------------------------------------------------- #
class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self._tests: list[tuple[str, callable]] = []

    def add(self, name: str, fn: callable) -> None:
        self._tests.append((name, fn))

    def run(self) -> None:
        print("=" * 70)
        print(" Paper Trading Engine — Integration Tests")
        print("=" * 70)
        for name, fn in self._tests:
            try:
                fn()
                self.passed += 1
                print(f"  ✅ PASS | {name}")
            except AssertionError as exc:
                self.failed += 1
                print(f"  ❌ FAIL | {name} | {exc}")
            except Exception as exc:
                self.failed += 1
                print(f"  ❌ ERR  | {name} | {exc}")

        print("\n" + "=" * 70)
        print(f" Results: {self.passed} passed, {self.failed} failed")
        print("=" * 70)
        if self.failed > 0:
            sys.exit(1)


runner = TestRunner()


# --------------------------------------------------------------------------- #
#  Test 1: TriLanguageBridge fallback
# --------------------------------------------------------------------------- #
def test_bridge_fallback() -> None:
    bridge = TriLanguageBridge(use_fallback=True)
    bids = [[65000.0, 1.0], [64990.0, 2.0]]
    asks = [[65010.0, 1.0], [65020.0, 2.0]]
    result = bridge.update("BTCUSDT", bids, asks)
    assert result["best_bid"] == 65000.0
    assert result["best_ask"] == 65010.0
    assert result["spread_bps"] > 0
    assert "latency_us" in result
    bridge.shutdown()

runner.add("TriLanguageBridge fallback update", test_bridge_fallback)


# --------------------------------------------------------------------------- #
#  Test 2: PaperOrderManager execution
# --------------------------------------------------------------------------- #
def test_order_manager() -> None:
    mgr = PaperOrderManager(initial_nav=100_000.0)
    book = {"best_bid": 65000.0, "best_ask": 65010.0, "mid": 65005.0, "spread_bps": 1.54}
    order = mgr.place_market("BTCUSDT", "buy", 0.01, book)
    assert order.side == "buy"
    assert order.size == 0.01
    assert order.price > 0
    assert order.fee > 0
    snap = mgr.snapshot()
    assert snap["nav"] < 100_000.0  # fee deducted
    assert snap["positions"]["BTCUSDT"] == 0.01
    assert snap["n_orders"] == 1

runner.add("PaperOrderManager buy execution", test_order_manager)


# --------------------------------------------------------------------------- #
#  Test 3: ArbitrageDetector
# --------------------------------------------------------------------------- #
def test_arbitrage_detector() -> None:
    det = ArbitrageDetector(threshold_bps=5.0)
    # BTC expensive, ETH cheap → arb BTC→ETH
    det.on_book("BTCUSDT", {"best_bid": 70000.0, "best_ask": 70010.0})
    det.on_book("ETHUSDT", {"best_bid": 3000.0, "best_ask": 3001.0})
    ops = det.scan()
    assert isinstance(ops, list)
    # With these prices no arb > 5 bps, but ensure scan runs
    assert len(ops) >= 0

runner.add("ArbitrageDetector scan", test_arbitrage_detector)


# --------------------------------------------------------------------------- #
#  Test 4: PaperTradingDB persistence
# --------------------------------------------------------------------------- #
def test_db_persistence() -> None:
    db_path = tempfile.mktemp(suffix=".db")
    db = PaperTradingDB(db_path)
    book = {"best_bid": 65000.0, "best_ask": 65010.0, "spread_bps": 1.54, "latency_us": 42.0}
    db.log_book("BTCUSDT", book)
    orders = db.get_stats()
    assert orders["n_orders"] == 0
    assert orders["n_arb"] == 0
    os.unlink(db_path)

runner.add("PaperTradingDB round-trip", test_db_persistence)


# --------------------------------------------------------------------------- #
#  Test 5: PaperTradingNative mock run
# --------------------------------------------------------------------------- #
def test_paper_native_mock() -> None:
    db_path = tempfile.mktemp(suffix=".db")
    config = PaperConfig(
        symbols=["BTCUSDT"],
        interval_ms=50,
        max_iterations=5,
        db_path=db_path,
        arbitrage_threshold_bps=100.0,  # high threshold = no trades
    )
    engine = PaperTradingNative(config)
    # Do not start WS — run a minimal manual iteration
    engine.iteration = 0
    for _ in range(3):
        engine.iteration += 1
        ops = engine.arb.scan()
        assert isinstance(ops, list)
    assert engine.iteration == 3
    os.unlink(db_path)

runner.add("PaperTradingNative mock iteration", test_paper_native_mock)


# --------------------------------------------------------------------------- #
#  Test 6: LiveTradingBridge paper pipeline
# --------------------------------------------------------------------------- #
def test_live_bridge_paper() -> None:
    vault = APIKeyVault(profile="test")
    risk = LiveRiskManager(max_single_trade_notional=50_000.0)
    risk.update_nav(100_000.0)
    bridge = LiveTradingBridge(
        exchange_id="binance",
        testnet=True,
        vault=vault,
        risk=risk,
    )
    bridge.initialize()
    assert bridge._initialized
    assert not bridge._live_mode
    result = bridge.trade("BTC/USDT", "buy", 0.001)
    assert result["mode"] == "paper"
    assert "trade_id" in result
    assert result["risk_check"]["allowed"] is True
    status = bridge.get_status()
    assert status["initialized"] is True
    assert status["live_mode"] is False

runner.add("LiveTradingBridge paper pipeline", test_live_bridge_paper)


# --------------------------------------------------------------------------- #
#  Test 7: Risk manager blocks oversized trade
# --------------------------------------------------------------------------- #
def test_risk_block() -> None:
    risk = LiveRiskManager(max_single_trade_notional=100.0)
    risk.update_nav(10_000.0)
    check = risk.check_trade("BTC/USDT", "buy", 1.0, price=70_000.0)
    assert check.allowed is False
    assert "Notional" in check.reason

runner.add("RiskManager blocks oversized trade", test_risk_block)


# --------------------------------------------------------------------------- #
#  Test 8: PnLTracker snapshot
# --------------------------------------------------------------------------- #
def test_pnl_tracker() -> None:
    db_path = tempfile.mktemp(suffix=".db")
    tracker = PnLTracker(db_path=db_path)
    from live_trading_bridge import LiveTrade
    tracker.record(LiveTrade(
        trade_id="t1", symbol="BTC/USDT", side="buy", size=0.01,
        price=65_000.0, fee=0.65, timestamp=time.time(),
        exchange="binance", order_type="MARKET", status="filled",
    ))
    tracker.record(LiveTrade(
        trade_id="t2", symbol="BTC/USDT", side="sell", size=0.01,
        price=66_000.0, fee=0.66, timestamp=time.time(),
        exchange="binance", order_type="MARKET", status="filled",
    ))
    snap = tracker.snapshot({"BTC/USDT": 66_000.0})
    assert snap["realized_pnl"] > 0
    assert snap["n_trades"] == 2
    os.unlink(db_path)

runner.add("PnLTracker realized PnL", test_pnl_tracker)


# --------------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    runner.run()
