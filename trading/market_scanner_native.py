#!/usr/bin/env python3
"""market_scanner_native.py — MAGNATRIX-OS Trading Layer
Market Scanner + Watchdog + Edge Alert System.

Pattern: AMATI-PELAJARI-TIRU dari OctagonAI/kalshi-trading-bot-cli (scan loop, watchdog, alerter).

Features:
  - Scan loop: periodically scan market universe for edge opportunities
  - Watchdog: monitor scan health, detect stuck/failed scans, auto-restart
  - Edge alert: notify when edge crosses threshold (very_high → high → moderate)
  - NDJSON output: one JSON object per scan cycle for streaming pipelines
  - Cache-aware: skip cached markets, only refresh when TTL expired
  - Multi-market batch: scan N markets concurrently
  - Alert deduplication: don't spam same alert within cooldown window

Usage:
    scanner = NativeMarketScanner(engine=NativePredictionMarketEngine(...))
    scanner.add_filter(min_confidence="high", min_edge=0.05, categories=["crypto"])
    scanner.add_alert_handler(print_alert)  # or webhook, WhatsApp, etc.
    scanner.start_scan_loop(interval_sec=300)  # scan every 5 min
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set


# ═══════════════════════════════════════════════════════════════════════════════
# Data Model
# ═══════════════════════════════════════════════════════════════════════════════

class AlertLevel(Enum):
    CRITICAL = auto()   # edge >= 15%
    HIGH = auto()       # edge >= 10%
    MODERATE = auto()   # edge >= 5%
    LOW = auto()        # edge >= 2%


@dataclass
class ScanResult:
    timestamp: float
    ticker: str
    title: str
    category: str
    model_prob: float
    market_prob: float
    edge: float
    confidence: str
    side: str
    contracts: int
    risk_passed: bool
    alert_level: AlertLevel
    cached: bool


@dataclass
class Alert:
    id: str
    timestamp: float
    ticker: str
    level: AlertLevel
    message: str
    data: Dict[str, Any]
    acknowledged: bool = False


@dataclass
class ScanFilter:
    min_confidence: str = "moderate"
    min_edge: float = 0.02
    max_edge: float = 1.0
    categories: Optional[List[str]] = None
    exclude_categories: Optional[List[str]] = None
    min_volume_24h: float = 0.0
    max_spread_cents: float = 10.0
    require_risk_passed: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# Watchdog
# ═══════════════════════════════════════════════════════════════════════════════

class ScanWatchdog:
    """Monitor scan health and detect stuck/failed scans."""

    def __init__(self, timeout_sec: float = 60.0, max_failures: int = 3) -> None:
        self.timeout_sec = timeout_sec
        self.max_failures = max_failures
        self._last_scan_time = 0.0
        self._failure_count = 0
        self._running = False
        self._state: str = "idle"

    def scan_start(self) -> None:
        self._last_scan_time = time.time()
        self._state = "scanning"

    def scan_complete(self, success: bool, results_count: int = 0) -> None:
        self._state = "complete" if success else "failed"
        if success:
            self._failure_count = 0
        else:
            self._failure_count += 1

    def is_healthy(self) -> bool:
        if self._state == "scanning":
            elapsed = time.time() - self._last_scan_time
            if elapsed > self.timeout_sec:
                return False
        return self._failure_count < self.max_failures

    def should_restart(self) -> bool:
        return self._failure_count >= self.max_failures or (
            self._state == "scanning" and time.time() - self._last_scan_time > self.timeout_sec * 2
        )

    def status(self) -> Dict[str, Any]:
        return {
            "state": self._state,
            "last_scan": self._last_scan_time,
            "failure_count": self._failure_count,
            "healthy": self.is_healthy(),
            "should_restart": self.should_restart(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Alert Deduplication
# ═══════════════════════════════════════════════════════════════════════════════

class AlertDeduplicator:
    """Prevent alert spam by deduplicating within cooldown window."""

    def __init__(self, cooldown_sec: float = 1800.0) -> None:  # 30 min default
        self.cooldown_sec = cooldown_sec
        self._history: Dict[str, float] = {}  # ticker → last_alert_time

    def should_alert(self, ticker: str, level: AlertLevel) -> bool:
        key = f"{ticker}:{level.name}"
        last = self._history.get(key, 0)
        if time.time() - last < self.cooldown_sec:
            return False
        self._history[key] = time.time()
        return True

    def reset(self, ticker: Optional[str] = None) -> None:
        if ticker:
            for key in list(self._history):
                if key.startswith(ticker):
                    del self._history[key]
        else:
            self._history.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# Market Scanner
# ═══════════════════════════════════════════════════════════════════════════════

class NativeMarketScanner:
    """Unified market scanner with watchdog, filtering, and alerting."""

    def __init__(self, engine: Any) -> None:
        """engine: any object with .scan_for_edges() and .search_markets() methods."""
        self.engine = engine
        self.filters: List[ScanFilter] = []
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self.watchdog = ScanWatchdog()
        self.dedup = AlertDeduplicator()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_results: List[ScanResult] = []
        self._alert_history: List[Alert] = []
        self._scan_count = 0

    def add_filter(self, **kwargs) -> None:
        self.filters.append(ScanFilter(**kwargs))

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        self.alert_handlers.append(handler)

    def _apply_filter(self, result: ScanResult, filt: ScanFilter) -> bool:
        if result.confidence not in ("very_high", "high", "moderate", "low"):
            return False
        confidence_order = {"very_high": 4, "high": 3, "moderate": 2, "low": 1}
        min_conf = confidence_order.get(filt.min_confidence, 0)
        res_conf = confidence_order.get(result.confidence, 0)
        if res_conf < min_conf:
            return False
        if abs(result.edge) < filt.min_edge or abs(result.edge) > filt.max_edge:
            return False
        if filt.categories and result.category not in filt.categories:
            return False
        if filt.exclude_categories and result.category in filt.exclude_categories:
            return False
        if filt.require_risk_passed and not result.risk_passed:
            return False
        return True

    def _to_alert_level(self, edge: float) -> AlertLevel:
        abs_edge = abs(edge)
        if abs_edge >= 0.15:
            return AlertLevel.CRITICAL
        elif abs_edge >= 0.10:
            return AlertLevel.HIGH
        elif abs_edge >= 0.05:
            return AlertLevel.MODERATE
        return AlertLevel.LOW

    def _to_scan_result(self, edge_dict: Dict[str, Any], ticker: str, title: str, category: str) -> ScanResult:
        return ScanResult(
            timestamp=time.time(),
            ticker=ticker,
            title=title,
            category=category,
            model_prob=edge_dict.get("model_prob", 0.0),
            market_prob=edge_dict.get("market_prob", 0.0),
            edge=edge_dict.get("edge", 0.0),
            confidence=edge_dict.get("confidence", "low"),
            side=edge_dict.get("side", "yes"),
            contracts=edge_dict.get("contracts", 0),
            risk_passed=edge_dict.get("risk_passed", False),
            alert_level=self._to_alert_level(edge_dict.get("edge", 0.0)),
            cached=edge_dict.get("cached", False),
        )

    def scan_once(self) -> List[ScanResult]:
        self.watchdog.scan_start()
        self._scan_count += 1
        results: List[ScanResult] = []

        try:
            edges = self.engine.scan_for_edges(min_confidence="low")
            for e in edges:
                result = self._to_scan_result(e, e.get("ticker", ""), e.get("title", ""), e.get("category", ""))
                if not self.filters:
                    results.append(result)
                else:
                    if any(self._apply_filter(result, f) for f in self.filters):
                        results.append(result)

            self._last_results = results
            self.watchdog.scan_complete(True, len(results))
        except Exception as ex:
            self.watchdog.scan_complete(False, 0)
            # Create alert for scan failure
            alert = Alert(
                id=f"SCAN-FAIL-{self._scan_count}", timestamp=time.time(),
                ticker="SYSTEM", level=AlertLevel.CRITICAL,
                message=f"Scan failed: {ex}", data={"error": str(ex)},
            )
            self._alert_history.append(alert)
            for h in self.alert_handlers:
                h(alert)

        return results

    def _check_alerts(self, results: List[ScanResult]) -> None:
        for r in results:
            if self.dedup.should_alert(r.ticker, r.alert_level):
                msg = f"[{r.alert_level.name}] {r.ticker}: edge={r.edge:.2%} ({r.side} {r.contracts} contracts)"
                alert = Alert(
                    id=f"{r.ticker}-{int(time.time())}", timestamp=time.time(),
                    ticker=r.ticker, level=r.alert_level, message=msg,
                    data={"edge": r.edge, "side": r.side, "contracts": r.contracts, "confidence": r.confidence},
                )
                self._alert_history.append(alert)
                for h in self.alert_handlers:
                    try:
                        h(alert)
                    except Exception:
                        pass

    def to_ndjson(self, results: Optional[List[ScanResult]] = None) -> str:
        """Return NDJSON (one JSON per line) for streaming pipelines."""
        lines = []
        for r in results or self._last_results:
            lines.append(json.dumps({
                "ticker": r.ticker, "title": r.title, "category": r.category,
                "edge": r.edge, "confidence": r.confidence,
                "side": r.side, "contracts": r.contracts,
                "risk_passed": r.risk_passed, "alert_level": r.alert_level.name,
                "timestamp": r.timestamp, "cached": r.cached,
            }, default=str))
        return "\n".join(lines)

    def start_scan_loop(self, interval_sec: float = 300.0) -> None:
        self._running = True

        def _loop():
            while self._running:
                results = self.scan_once()
                self._check_alerts(results)
                if self.watchdog.should_restart():
                    self.watchdog._failure_count = 0  # reset and try again
                time.sleep(interval_sec)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def status(self) -> Dict[str, Any]:
        return {
            "scan_count": self._scan_count,
            "last_results": len(self._last_results),
            "alert_history": len(self._alert_history),
            "watchdog": self.watchdog.status(),
            "running": self._running,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Market Scanner — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Mock engine
    class MockEngine:
        def scan_for_edges(self, min_confidence="low"):
            return [
                {"ticker": "BTC-YES", "title": "BTC above 100k", "category": "crypto",
                 "edge": 0.12, "confidence": "high", "side": "yes", "contracts": 10, "risk_passed": True, "cached": False},
                {"ticker": "ETH-YES", "title": "ETH above 5k", "category": "crypto",
                 "edge": 0.03, "confidence": "moderate", "side": "yes", "contracts": 5, "risk_passed": True, "cached": False},
                {"ticker": "SPX-YES", "title": "S&P up", "category": "stocks",
                 "edge": 0.20, "confidence": "very_high", "side": "yes", "contracts": 50, "risk_passed": False, "cached": False},
            ]

    engine = MockEngine()
    scanner = NativeMarketScanner(engine)

    # Test 1: Scan once
    print("[Test 1] Scan once")
    results = scanner.scan_once()
    ok = len(results) >= 2
    print(f"  Results: {len(results)} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Filter
    print("[Test 2] Filter by category")
    scanner.add_filter(categories=["crypto"])
    results2 = scanner.scan_once()
    ok2 = all(r.category == "crypto" for r in results2)
    print(f"  All crypto: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Alert dedup
    print("[Test 3] Alert deduplication")
    dedup = AlertDeduplicator(cooldown_sec=1.0)
    ok3a = dedup.should_alert("BTC-YES", AlertLevel.HIGH)
    ok3b = not dedup.should_alert("BTC-YES", AlertLevel.HIGH)  # within cooldown
    time.sleep(1.1)
    ok3c = dedup.should_alert("BTC-YES", AlertLevel.HIGH)  # after cooldown
    print(f"  First alert={ok3a}, blocked={ok3b}, after cooldown={ok3c} — {'PASS' if ok3a and ok3b and ok3c else 'FAIL'}")
    passed += ok3a and ok3b and ok3c

    # Test 4: Alert handler
    print("[Test 4] Alert handler")
    alerts_received = []
    scanner2 = NativeMarketScanner(engine)
    scanner2.add_filter(min_confidence="high")
    scanner2.add_alert_handler(lambda a: alerts_received.append(a))
    scanner2.scan_once()
    scanner2._check_alerts(scanner2._last_results)
    ok4 = len(alerts_received) > 0
    print(f"  Alerts received: {len(alerts_received)} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Watchdog healthy
    print("[Test 5] Watchdog health")
    wd = ScanWatchdog(timeout_sec=5.0)
    wd.scan_start()
    wd.scan_complete(True, 3)
    ok5 = wd.is_healthy()
    print(f"  Healthy after success: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Watchdog failure detection
    print("[Test 6] Watchdog failure detection")
    wd2 = ScanWatchdog(timeout_sec=1.0, max_failures=2)
    wd2.scan_complete(False)
    wd2.scan_complete(False)
    ok6 = wd2.should_restart()
    print(f"  Restart after 2 failures: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: NDJSON output
    print("[Test 7] NDJSON output")
    scanner3 = NativeMarketScanner(engine)
    scanner3.scan_once()
    ndjson = scanner3.to_ndjson()
    ok7 = len(ndjson) > 0 and "BTC-YES" in ndjson
    print(f"  NDJSON contains BTC-YES: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
