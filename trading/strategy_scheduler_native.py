#!/usr/bin/env python3
"""strategy_scheduler_native.py — MAGNATRIX-OS Trading Layer
Strategy Scheduler & Market Regime Filter.

Features:
  - Time-based activation: configurable trading windows (e.g. 09:00-16:00 UTC)
  - Market regime detection: bull / bear / ranging via SMA/EMA crossover + ADX
  - Regime → strategy mapping: activate different strategies per regime
  - News blackout periods: configurable calendar blackouts (FOMC, NFP, etc.)
  - Strategy lifecycle: START → RUN → STOP → COOLDOWN
  - Position sizing adjustment per regime (more conservative in bear/range)

Usage:
    scheduler = NativeStrategyScheduler()
    scheduler.add_strategy("trend_follow", TrendFollowStrategy(),
                           active_hours=[(9, 16)], regimes=["bull", "bear"])
    scheduler.add_blackout("FOMC", day_of_week=2, hour=14, duration_minutes=60)
    scheduler.run(register=lambda s: print(f"Active: {s}"))
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

class Regime(Enum):
    BULL = auto()
    BEAR = auto()
    RANGE = auto()
    UNKNOWN = auto()


class StrategyState(Enum):
    IDLE = auto()
    STARTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    COOLDOWN = auto()


@dataclass
class TimeWindow:
    start_hour: int
    end_hour: int
    start_minute: int = 0
    end_minute: int = 0

    def contains(self, hour: int, minute: int) -> bool:
        start = self.start_hour * 60 + self.start_minute
        end = self.end_hour * 60 + self.end_minute
        now = hour * 60 + minute
        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end


@dataclass
class BlackoutEvent:
    name: str
    month: Optional[int] = None           # 1-12, None = any month
    day: Optional[int] = None             # 1-31, None = any day
    day_of_week: Optional[int] = None     # 0=Mon, None = any
    hour: int = 0
    minute: int = 0
    duration_minutes: int = 60
    timezone: str = "UTC"


@dataclass
class StrategyConfig:
    name: str
    strategy_obj: Any
    active_hours: List[TimeWindow] = field(default_factory=list)
    regimes: List[Regime] = field(default_factory=lambda: [Regime.BULL, Regime.BEAR, Regime.RANGE])
    max_positions: int = 1
    position_size_pct: float = 0.01       # 1% of equity per trade
    cooldown_sec: int = 300               # 5 min between re-activation
    enabled: bool = True


# ══════════════════════════════════════════════════════════════════════════════
# Market Regime Detector
# ══════════════════════════════════════════════════════════════════════════════

class RegimeDetector:
    """Detect market regime using SMA/EMA crossover + ADX proxy."""

    def __init__(self, fast: int = 10, slow: int = 30, adx_period: int = 14) -> None:
        self.fast = fast
        self.slow = slow
        self.adx_period = adx_period
        self._history: List[float] = []
        self._last_regime = Regime.UNKNOWN

    def update(self, price: float) -> Regime:
        self._history.append(price)
        if len(self._history) > self.slow * 3:
            self._history = self._history[-self.slow * 3:]
        return self.detect()

    def detect(self) -> Regime:
        if len(self._history) < self.slow:
            return Regime.UNKNOWN

        fast_sma = self._sma(self._history, self.fast)
        slow_sma = self._sma(self._history, self.slow)
        fast_ema = self._ema(self._history, self.fast)
        slow_ema = self._ema(self._history, self.slow)

        adx = self._adx_proxy(self._history, self.adx_period)

        if fast_ema > slow_ema and fast_sma > slow_sma and adx > 20:
            regime = Regime.BULL
        elif fast_ema < slow_ema and fast_sma < slow_sma and adx > 20:
            regime = Regime.BEAR
        else:
            regime = Regime.RANGE

        self._last_regime = regime
        return regime

    def _sma(self, data: List[float], period: int) -> float:
        return sum(data[-period:]) / period

    def _ema(self, data: List[float], period: int) -> float:
        k = 2 / (period + 1)
        ema = data[0]
        for p in data[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    def _adx_proxy(self, data: List[float], period: int) -> float:
        """Simplified ADX: average of directional movement."""
        if len(data) < period + 1:
            return 0.0
        dm_sum = 0.0
        for i in range(-period, 0):
            up = data[i] - data[i - 1]
            down = data[i - 1] - data[i]
            dm_plus = max(up, 0) if up > down else 0
            dm_minus = max(down, 0) if down > up else 0
            dm_sum += abs(dm_plus - dm_minus)
        return dm_sum / period * 100


# ══════════════════════════════════════════════════════════════════════════════
# Strategy Scheduler
# ══════════════════════════════════════════════════════════════════════════════

class NativeStrategyScheduler:
    """Schedule and manage trading strategies based on time, regime, and blackouts."""

    def __init__(self) -> None:
        self._strategies: Dict[str, StrategyConfig] = {}
        self._blackouts: List[BlackoutEvent] = []
        self._states: Dict[str, StrategyState] = {}
        self._last_activated: Dict[str, float] = {}
        self._regime_detector = RegimeDetector()
        self._current_regime = Regime.UNKNOWN
        self._running = False

    # ── Configuration ─────────────────────────────────────────────────────────

    def add_strategy(self, name: str, strategy_obj: Any,
                     active_hours: Optional[List[Tuple[int, int, int, int]]] = None,
                     regimes: Optional[List[str]] = None,
                     max_positions: int = 1,
                     position_size_pct: float = 0.01,
                     cooldown_sec: int = 300) -> None:
        """Add a strategy with scheduling config.
        active_hours: [(start_h, start_m, end_h, end_m), ...]
        regimes: ["bull", "bear", "range"]
        """
        windows = []
        if active_hours:
            for sh, sm, eh, em in active_hours:
                windows.append(TimeWindow(start_hour=sh, end_hour=eh, start_minute=sm, end_minute=em))
        regime_list = []
        if regimes:
            for r in regimes:
                regime_list.append(Regime[r.upper()])
        else:
            regime_list = [Regime.BULL, Regime.BEAR, Regime.RANGE]

        self._strategies[name] = StrategyConfig(
            name=name, strategy_obj=strategy_obj,
            active_hours=windows, regimes=regime_list,
            max_positions=max_positions,
            position_size_pct=position_size_pct,
            cooldown_sec=cooldown_sec,
        )
        self._states[name] = StrategyState.IDLE
        self._last_activated[name] = 0.0

    def add_blackout(self, name: str, month: Optional[int] = None,
                     day: Optional[int] = None, day_of_week: Optional[int] = None,
                     hour: int = 0, minute: int = 0,
                     duration_minutes: int = 60) -> None:
        self._blackouts.append(BlackoutEvent(
            name=name, month=month, day=day, day_of_week=day_of_week,
            hour=hour, minute=minute, duration_minutes=duration_minutes,
        ))

    def set_regime(self, regime: Regime) -> None:
        """Manually override regime (or use update_price for auto)."""
        self._current_regime = regime

    def update_price(self, price: float) -> Regime:
        self._current_regime = self._regime_detector.update(price)
        return self._current_regime

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def run(self, tick_interval: float = 1.0,
            register: Optional[Callable[[str, Any], None]] = None,
            unregister: Optional[Callable[[str], None]] = None) -> None:
        """Main scheduler loop. Call in a thread or async context."""
        self._running = True
        while self._running:
            self._tick(register, unregister)
            time.sleep(tick_interval)

    def _tick(self, register: Optional[Callable] = None,
              unregister: Optional[Callable] = None) -> None:
        now = time.gmtime()
        in_blackout = self._check_blackout(now)
        regime = self._current_regime

        for name, cfg in self._strategies.items():
            if not cfg.enabled:
                continue
            state = self._states[name]
            should_run = self._should_run(cfg, now, regime, in_blackout)

            if should_run and state in (StrategyState.IDLE, StrategyState.COOLDOWN):
                # Activate
                if time.time() - self._last_activated[name] >= cfg.cooldown_sec:
                    self._states[name] = StrategyState.RUNNING
                    self._last_activated[name] = time.time()
                    if register:
                        register(name, cfg.strategy_obj)
            elif not should_run and state == StrategyState.RUNNING:
                # Deactivate
                self._states[name] = StrategyState.COOLDOWN
                if unregister:
                    unregister(name)

    def _should_run(self, cfg: StrategyConfig, now: time.struct_time,
                    regime: Regime, in_blackout: bool) -> bool:
        if in_blackout:
            return False
        if regime not in cfg.regimes:
            return False
        if not cfg.active_hours:
            return True
        for window in cfg.active_hours:
            if window.contains(now.tm_hour, now.tm_min):
                return True
        return False

    def _check_blackout(self, now: time.struct_time) -> bool:
        for b in self._blackouts:
            if b.month is not None and now.tm_mon != b.month:
                continue
            if b.day is not None and now.tm_mday != b.day:
                continue
            if b.day_of_week is not None and now.tm_wday != b.day_of_week:
                continue
            start_min = b.hour * 60 + b.minute
            current_min = now.tm_hour * 60 + now.tm_min
            if start_min <= current_min < start_min + b.duration_minutes:
                return True
        return False

    def stop(self) -> None:
        self._running = False

    def status(self) -> Dict[str, Any]:
        return {
            "regime": self._current_regime.name,
            "strategies": {
                name: {"state": self._states[name].name, "enabled": cfg.enabled}
                for name, cfg in self._strategies.items()
            },
            "blackouts": [b.name for b in self._blackouts],
        }

    def position_size_for(self, strategy_name: str, equity: float) -> float:
        """Return position size in base currency for a strategy."""
        cfg = self._strategies.get(strategy_name)
        if not cfg:
            return 0.0
        # Adjust size by regime: 50% smaller in bear/range
        multiplier = 1.0 if self._current_regime == Regime.BULL else 0.5
        return equity * cfg.position_size_pct * multiplier


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

class _DummyStrategy:
    def __init__(self):
        self.active = False

    def start(self):
        self.active = True

    def stop(self):
        self.active = False


def _self_test() -> int:
    print("=" * 60)
    print("Native Strategy Scheduler — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Test 1: TimeWindow
    print("[Test 1] TimeWindow overlap")
    w = TimeWindow(start_hour=9, end_hour=16, start_minute=0, end_minute=0)
    ok = w.contains(10, 30) and not w.contains(17, 0)
    print(f"  10:30 in [9-16]: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Regime detection (bull)
    print("[Test 2] Regime detection (bull)")
    det = RegimeDetector(fast=3, slow=5)
    prices = list(range(100, 120))  # 20 points strong uptrend
    for p in prices:
        regime = det.update(p)
    ok2 = regime == Regime.BULL
    print(f"  Trending up → BULL: {ok2} ({regime.name}) — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Regime detection (bear)
    print("[Test 3] Regime detection (bear)")
    det2 = RegimeDetector(fast=3, slow=5)
    prices_down = list(range(120, 100, -1))  # 20 points strong downtrend
    for p in prices_down:
        regime2 = det2.update(p)
    ok3 = regime2 == Regime.BEAR
    print(f"  Trending down → BEAR: {ok3} ({regime2.name}) — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Scheduler strategy activation
    print("[Test 4] Strategy activation")
    sched = NativeStrategyScheduler()
    strat = _DummyStrategy()
    sched.add_strategy("trend", strat, active_hours=[(0, 0, 23, 59)], regimes=["bull"])
    sched.set_regime(Regime.BULL)
    active = []
    sched._tick(register=lambda n, s: active.append(n))
    ok4 = "trend" in active
    print(f"  Strategy activated: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Blackout blocks activation
    print("[Test 5] Blackout blocking")
    sched2 = NativeStrategyScheduler()
    sched2.add_strategy("trend", _DummyStrategy(), active_hours=[(0, 0, 23, 59)], regimes=["bull"])
    sched2.add_blackout("FOMC", day_of_week=0, hour=0, minute=0, duration_minutes=1440)
    sched2.set_regime(Regime.BULL)
    active2 = []
    now = time.struct_time((2024, 1, 1, 0, 0, 0, 0, 0, 0))  # Monday
    in_bo = sched2._check_blackout(now)
    ok5 = in_bo
    print(f"  Blackout detected Monday: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Position sizing by regime
    print("[Test 6] Position sizing by regime")
    sched3 = NativeStrategyScheduler()
    sched3.add_strategy("trend", _DummyStrategy(), position_size_pct=0.02)
    sched3.set_regime(Regime.BULL)
    size_bull = sched3.position_size_for("trend", 10000)
    sched3.set_regime(Regime.BEAR)
    size_bear = sched3.position_size_for("trend", 10000)
    ok6 = size_bull == 200.0 and size_bear == 100.0
    print(f"  BULL={size_bull}, BEAR={size_bear}: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Status report
    print("[Test 7] Status report")
    st = sched.status()
    ok7 = "regime" in st and "strategies" in st
    print(f"  Status valid: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
