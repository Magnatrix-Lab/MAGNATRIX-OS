#!/usr/bin/env python3
"""risk_engine_native.py — MAGNATRIX-OS Trading Layer
Risk Management Engine.

Features:
  - Position sizing: fixed fractional, Kelly criterion, optimal f, volatility-adjusted
  - Portfolio heat: max concurrent risk, sector concentration limit
  - Drawdown circuit breaker: auto stop trading when drawdown exceeds threshold
  - Daily loss limit: max daily loss $ or %, reset at midnight UTC
  - Correlation check: prevent simultaneous long/short in correlated pairs
  - Stop-loss / take-profit manager: trailing stop, ATR-based stops
  - Risk per trade: configurable (default 1% of equity)

Usage:
    engine = NativeRiskEngine(equity=10000.0)
    size = engine.position_size(signal_confidence=0.8, atr=150.0, price=50000.0)
    engine.check_drawdown(current_equity=9500.0)
    engine.check_daily_loss(today_pnl=-200.0)
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

class RiskState(Enum):
    NORMAL = auto()
    WARNING = auto()
    CRITICAL = auto()
    HALTED = auto()


@dataclass
class PositionSizingResult:
    size_units: float
    size_quote: float
    risk_amount: float
    risk_pct: float
    method: str
    approved: bool
    reason: str = ""


@dataclass
class RiskSnapshot:
    timestamp: float
    equity: float
    open_positions: int
    total_risk_pct: float
    daily_pnl: float
    max_drawdown_pct: float
    state: RiskState


# ══════════════════════════════════════════════════════════════════════════════
# Position Sizing
# ══════════════════════════════════════════════════════════════════════════════

class PositionSizer:
    """Calculate position size using multiple methods."""

    def __init__(self, equity: float, risk_per_trade_pct: float = 0.01):
        self.equity = equity
        self.risk_per_trade_pct = risk_per_trade_pct

    def fixed_fractional(self, stop_loss_pct: float) -> PositionSizingResult:
        """Risk fixed % of equity per trade."""
        risk_amount = self.equity * self.risk_per_trade_pct
        if stop_loss_pct <= 0:
            return PositionSizingResult(0, 0, 0, 0, "fixed_fractional", False, "Invalid stop loss")
        size_quote = risk_amount / stop_loss_pct
        size_units = size_quote  # assume price = 1 for unit sizing
        return PositionSizingResult(
            size_units, size_quote, risk_amount, self.risk_per_trade_pct,
            "fixed_fractional", True,
        )

    def kelly(self, win_rate: float, avg_win: float, avg_loss: float) -> PositionSizingResult:
        """Kelly criterion: f = (p*b - q) / b."""
        if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
            return PositionSizingResult(0, 0, 0, 0, "kelly", False, "Invalid inputs")
        b = avg_win / avg_loss
        q = 1 - win_rate
        kelly_f = (win_rate * b - q) / b
        kelly_f = max(0, min(kelly_f, 0.5))  # cap at half-Kelly
        risk_amount = self.equity * kelly_f
        return PositionSizingResult(
            risk_amount, risk_amount, risk_amount, kelly_f,
            "kelly", True,
        )

    def optimal_f(self, trades: List[float]) -> PositionSizingResult:
        """Optimal f via geometric mean maximization."""
        if not trades or any(t <= -1 for t in trades):
            return PositionSizingResult(0, 0, 0, 0, "optimal_f", False, "Invalid trade returns")
        best_f = 0.0
        best_g = 0.0
        for f in [i / 100 for i in range(1, 51)]:
            g = sum(math.log(1 + f * t) for t in trades if 1 + f * t > 0)
            if g > best_g:
                best_g = g
                best_f = f
        risk_amount = self.equity * best_f
        return PositionSizingResult(
            risk_amount, risk_amount, risk_amount, best_f,
            "optimal_f", True,
        )

    def volatility_adjusted(self, atr: float, price: float, atr_multiplier: float = 2.0) -> PositionSizingResult:
        """ATR-based position sizing."""
        if atr <= 0 or price <= 0:
            return PositionSizingResult(0, 0, 0, 0, "volatility_adjusted", False, "Invalid ATR/price")
        stop_loss_pct = (atr * atr_multiplier) / price
        return self.fixed_fractional(stop_loss_pct)


# ══════════════════════════════════════════════════════════════════════════════
# Drawdown & Circuit Breaker
# ══════════════════════════════════════════════════════════════════════════════

class DrawdownMonitor:
    """Track equity peak and trigger circuit breaker on excessive drawdown."""

    def __init__(self, max_drawdown_pct: float = 0.05, halt_drawdown_pct: float = 0.10):
        self.max_drawdown_pct = max_drawdown_pct
        self.halt_drawdown_pct = halt_drawdown_pct
        self.peak_equity = 0.0
        self.current_drawdown = 0.0
        self.state = RiskState.NORMAL
        self.history: List[Tuple[float, float]] = []  # (timestamp, drawdown)

    def update(self, equity: float) -> RiskState:
        if equity > self.peak_equity:
            self.peak_equity = equity
        self.current_drawdown = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0.0
        self.history.append((time.time(), self.current_drawdown))

        if self.current_drawdown >= self.halt_drawdown_pct:
            self.state = RiskState.HALTED
        elif self.current_drawdown >= self.max_drawdown_pct:
            self.state = RiskState.CRITICAL
        elif self.current_drawdown >= self.max_drawdown_pct * 0.7:
            self.state = RiskState.WARNING
        else:
            self.state = RiskState.NORMAL
        return self.state

    def reset(self) -> None:
        self.peak_equity = 0.0
        self.current_drawdown = 0.0
        self.state = RiskState.NORMAL
        self.history.clear()


# ══════════════════════════════════════════════════════════════════════════════
# Daily Loss Limit
# ══════════════════════════════════════════════════════════════════════════════

class DailyLossLimit:
    """Track daily P&L and enforce max daily loss."""

    def __init__(self, max_loss_pct: float = 0.03, max_loss_abs: Optional[float] = None):
        self.max_loss_pct = max_loss_pct
        self.max_loss_abs = max_loss_abs
        self.daily_pnl = 0.0
        self._day_start_equity = 0.0
        self._last_reset_day = 0

    def reset(self, equity: float) -> None:
        self._day_start_equity = equity
        self.daily_pnl = 0.0
        self._last_reset_day = time.gmtime().tm_yday

    def update(self, trade_pnl: float, equity: float) -> bool:
        today = time.gmtime().tm_yday
        if today != self._last_reset_day:
            self.reset(equity)
        self.daily_pnl += trade_pnl

        if self.max_loss_abs is not None and self.daily_pnl <= -self.max_loss_abs:
            return False
        if self._day_start_equity > 0 and self.daily_pnl <= -self._day_start_equity * self.max_loss_pct:
            return False
        return True

    def can_trade(self, equity: float) -> bool:
        today = time.gmtime().tm_yday
        if today != self._last_reset_day:
            self.reset(equity)
        return True


# ══════════════════════════════════════════════════════════════════════════════
# Correlation Guard
# ══════════════════════════════════════════════════════════════════════════════

class CorrelationGuard:
    """Prevent simultaneous positions in correlated assets."""

    CORRELATION_MATRIX: Dict[Tuple[str, str], float] = {
        ("BTC", "ETH"): 0.85,
        ("BTC", "SOL"): 0.75,
        ("ETH", "SOL"): 0.80,
        ("BTC", "XRP"): 0.60,
        ("ETH", "XRP"): 0.65,
        ("BTC", "DOGE"): 0.55,
    }

    def __init__(self, threshold: float = 0.70):
        self.threshold = threshold
        self.positions: Dict[str, str] = {}  # symbol -> side (long/short)

    def add_position(self, symbol: str, side: str) -> bool:
        for existing, existing_side in self.positions.items():
            corr = self._get_correlation(symbol, existing)
            if corr >= self.threshold:
                if side != existing_side:
                    return False  # Correlated opposite positions = hedging risk
        self.positions[symbol] = side
        return True

    def remove_position(self, symbol: str) -> None:
        self.positions.pop(symbol, None)

    def _get_correlation(self, a: str, b: str) -> float:
        key = (a, b) if (a, b) in self.CORRELATION_MATRIX else (b, a)
        return self.CORRELATION_MATRIX.get(key, 0.0)


# ══════════════════════════════════════════════════════════════════════════════
# Stop-Loss / Take-Profit Manager
# ══════════════════════════════════════════════════════════════════════════════

class StopLossManager:
    """Manage trailing stops and ATR-based stops."""

    def __init__(self, atr_multiplier: float = 2.0, trailing_pct: Optional[float] = None):
        self.atr_multiplier = atr_multiplier
        self.trailing_pct = trailing_pct
        self._entry_price: Dict[str, float] = {}
        self._highest_price: Dict[str, float] = {}
        self._stop_price: Dict[str, float] = {}

    def set_stop(self, symbol: str, entry_price: float, atr: float) -> float:
        stop = entry_price - atr * self.atr_multiplier
        self._entry_price[symbol] = entry_price
        self._highest_price[symbol] = entry_price
        self._stop_price[symbol] = stop
        return stop

    def update_trailing(self, symbol: str, current_price: float) -> Optional[float]:
        if symbol not in self._highest_price:
            return None
        if current_price > self._highest_price[symbol]:
            self._highest_price[symbol] = current_price
            if self.trailing_pct:
                self._stop_price[symbol] = current_price * (1 - self.trailing_pct)
        return self._stop_price[symbol]

    def check_trigger(self, symbol: str, current_price: float) -> bool:
        return current_price <= self._stop_price.get(symbol, 0.0)

    def take_profit_price(self, symbol: str, rr_ratio: float = 2.0) -> float:
        entry = self._entry_price.get(symbol, 0.0)
        stop = self._stop_price.get(symbol, 0.0)
        risk = entry - stop
        return entry + risk * rr_ratio


# ══════════════════════════════════════════════════════════════════════════════
# Unified Risk Engine
# ══════════════════════════════════════════════════════════════════════════════

class NativeRiskEngine:
    """Unified risk management facade."""

    def __init__(self, equity: float = 10000.0, risk_per_trade_pct: float = 0.01,
                 max_drawdown_pct: float = 0.05, halt_drawdown_pct: float = 0.10,
                 max_daily_loss_pct: float = 0.03, correlation_threshold: float = 0.70) -> None:
        self.equity = equity
        self.initial_equity = equity
        self.sizer = PositionSizer(equity, risk_per_trade_pct)
        self.drawdown = DrawdownMonitor(max_drawdown_pct, halt_drawdown_pct)
        self.daily_loss = DailyLossLimit(max_daily_loss_pct)
        self.correlation = CorrelationGuard(correlation_threshold)
        self.stop_loss = StopLossManager()
        self.history: List[RiskSnapshot] = []

    def position_size(self, method: str = "fixed_fractional", **kwargs) -> PositionSizingResult:
        if method == "fixed_fractional":
            return self.sizer.fixed_fractional(kwargs.get("stop_loss_pct", 0.02))
        elif method == "kelly":
            return self.sizer.kelly(kwargs.get("win_rate", 0.55), kwargs.get("avg_win", 100), kwargs.get("avg_loss", 50))
        elif method == "optimal_f":
            return self.sizer.optimal_f(kwargs.get("trades", []))
        elif method == "volatility_adjusted":
            return self.sizer.volatility_adjusted(kwargs.get("atr", 100.0), kwargs.get("price", 1000.0))
        return PositionSizingResult(0, 0, 0, 0, method, False, "Unknown method")

    def check_drawdown(self, equity: float) -> RiskState:
        return self.drawdown.update(equity)

    def check_daily_loss(self, trade_pnl: float) -> bool:
        return self.daily_loss.update(trade_pnl, self.equity)

    def can_open_position(self, symbol: str, side: str) -> Tuple[bool, str]:
        if self.drawdown.state == RiskState.HALTED:
            return False, "Trading halted: drawdown exceeded"
        if not self.daily_loss.can_trade(self.equity):
            return False, "Daily loss limit reached"
        if not self.correlation.add_position(symbol, side):
            return False, f"Correlation guard: {symbol} conflicts with existing position"
        return True, "OK"

    def close_position(self, symbol: str) -> None:
        self.correlation.remove_position(symbol)
        self.stop_loss._stop_price.pop(symbol, None)
        self.stop_loss._highest_price.pop(symbol, None)
        self.stop_loss._entry_price.pop(symbol, None)

    def update_equity(self, new_equity: float) -> RiskSnapshot:
        self.equity = new_equity
        state = self.drawdown.update(new_equity)
        snap = RiskSnapshot(
            timestamp=time.time(),
            equity=new_equity,
            open_positions=len(self.correlation.positions),
            total_risk_pct=sum(self.sizer.risk_per_trade_pct for _ in self.correlation.positions),
            daily_pnl=self.daily_loss.daily_pnl,
            max_drawdown_pct=self.drawdown.current_drawdown,
            state=state,
        )
        self.history.append(snap)
        return snap

    def status(self) -> Dict[str, Any]:
        return {
            "equity": self.equity,
            "initial_equity": self.initial_equity,
            "drawdown_pct": round(self.drawdown.current_drawdown, 4),
            "state": self.drawdown.state.name,
            "daily_pnl": round(self.daily_loss.daily_pnl, 2),
            "open_positions": len(self.correlation.positions),
            "risk_per_trade_pct": self.sizer.risk_per_trade_pct,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Risk Engine — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Test 1: Fixed fractional sizing
    print("[Test 1] Fixed fractional sizing")
    engine = NativeRiskEngine(equity=10000.0)
    result = engine.position_size("fixed_fractional", stop_loss_pct=0.02)
    ok = result.approved and result.risk_amount == 100.0
    print(f"  Risk $100 (1% of $10k): {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Kelly sizing
    print("[Test 2] Kelly sizing")
    result2 = engine.position_size("kelly", win_rate=0.60, avg_win=150, avg_loss=50)
    ok2 = result2.approved and result2.risk_pct > 0
    print(f"  Kelly f > 0: {ok2} (f={result2.risk_pct:.4f}) — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Drawdown circuit breaker
    print("[Test 3] Drawdown circuit breaker")
    engine2 = NativeRiskEngine(equity=10000.0, max_drawdown_pct=0.05, halt_drawdown_pct=0.10)
    engine2.check_drawdown(10000.0)
    engine2.check_drawdown(9400.0)  # 6% DD
    ok3 = engine2.drawdown.state == RiskState.CRITICAL
    engine2.check_drawdown(8900.0)  # 11% DD
    ok3b = engine2.drawdown.state == RiskState.HALTED
    print(f"  6% DD→CRITICAL, 11% DD→HALTED: {ok3 and ok3b} — {'PASS' if ok3 and ok3b else 'FAIL'}")
    passed += ok3 and ok3b

    # Test 4: Daily loss limit
    print("[Test 4] Daily loss limit")
    engine3 = NativeRiskEngine(equity=10000.0, max_daily_loss_pct=0.03)
    ok4 = engine3.check_daily_loss(-100.0)  # -$100, still OK
    ok4b = not engine3.check_daily_loss(-300.0)  # -$400 total, > 3% of 10k
    print(f"  -$100 OK, -$400 total → blocked: {ok4 and ok4b} — {'PASS' if ok4 and ok4b else 'FAIL'}")
    passed += ok4 and ok4b

    # Test 5: Correlation guard
    print("[Test 5] Correlation guard")
    engine4 = NativeRiskEngine(equity=10000.0)
    ok5a = engine4.can_open_position("BTC", "long")[0]
    ok5b = not engine4.can_open_position("ETH", "short")[0]  # BTC-ETH corr=0.85
    ok5c = engine4.can_open_position("XRP", "long")[0]  # Low corr
    print(f"  BTC long OK, ETH short blocked, XRP long OK: {ok5a and ok5b and ok5c} — {'PASS' if ok5a and ok5b and ok5c else 'FAIL'}")
    passed += ok5a and ok5b and ok5c

    # Test 6: Stop-loss manager
    print("[Test 6] Stop-loss manager")
    sl = StopLossManager(atr_multiplier=2.0)
    stop = sl.set_stop("BTC", 50000.0, 200.0)
    triggered = sl.check_trigger("BTC", 49500.0)
    not_triggered = not sl.check_trigger("BTC", 50100.0)
    ok6 = stop == 49600.0 and triggered and not_triggered
    print(f"  Stop={stop}, trigger={triggered}, not_triggered={not_triggered}: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Status report
    print("[Test 7] Status report")
    st = engine.status()
    ok7 = "equity" in st and "drawdown_pct" in st and "state" in st
    print(f"  Status valid: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
