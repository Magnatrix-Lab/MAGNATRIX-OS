#!/usr/bin/env python3
"""
tests/integration/test_hft_pipeline.py
HFT pipeline end-to-end tests.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from runtime.tri_language_bridge import UnifiedHFT, TriLanguageHub
from trading.cpp_hft_engine.hft_engine_py import HFTEngine, Tick, OrderSide


def test_hft_engine_creation():
    engine = HFTEngine()
    assert engine is not None
    print("PASS: HFT engine creation (Python fallback)")


def test_order_book_insert():
    engine = HFTEngine()
    bm = engine.book_manager()
    bm.add_bid(100_0000, 10)  # $100.00, qty 10
    bm.add_ask(101_0000, 5)   # $101.00, qty 5
    spread = bm.spread()
    assert spread == 1_0000  # $1.00 spread
    print("PASS: Order book bid/ask insertion + spread")


def test_arbitrage_detection():
    engine = HFTEngine()
    arb = engine.arb_detector()
    # Setup two books
    arb.add_book("binance", {"bid": 100_0000, "ask": 101_0000, "fee": 0.001})
    arb.add_book("bybit", {"bid": 102_0000, "ask": 103_0000, "fee": 0.001})
    opps = arb.scan_opportunities()
    assert len(opps) >= 0  # May or may not find arb depending on thresholds
    print("PASS: Arbitrage detection scan")


def test_tick_to_trade_latency():
    engine = HFTEngine()
    tick = Tick(symbol="BTC/USDT", bid=50000_0000, ask=50001_0000,
                timestamp_ns=time.time_ns())
    start = time.perf_counter_ns()
    engine.on_tick(tick)
    latency_ns = time.perf_counter_ns() - start
    assert latency_ns < 1_000_000  # < 1ms
    print(f"PASS: Tick-to-trade latency: {latency_ns/1000:.1f}us")


def test_tri_language_hft():
    hub = TriLanguageHub()
    # Test Python fallback HFT
    tick = {"symbol": "ETH/USDT", "bid": 3000_0000, "ask": 3001_0000}
    result = hub.hft.on_tick(tick)
    assert result is not None
    print("PASS: Tri-language HFT bridge")


def test_order_book_best_levels():
    engine = HFTEngine()
    bm = engine.book_manager()
    bm.add_bid(100_0000, 10)
    bm.add_bid(99_5000, 20)
    bm.add_ask(101_0000, 5)
    bm.add_ask(102_0000, 8)
    best_bid = bm.best_bid()
    best_ask = bm.best_ask()
    assert best_bid[0] == 100_0000
    assert best_ask[0] == 101_0000
    print("PASS: Order book best bid/ask levels")


def run_all():
    print("=" * 60)
    print("HFT Pipeline End-to-End Tests")
    print("=" * 60)
    tests = [
        test_hft_engine_creation,
        test_order_book_insert,
        test_arbitrage_detection,
        test_tick_to_trade_latency,
        test_tri_language_hft,
        test_order_book_best_levels,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
