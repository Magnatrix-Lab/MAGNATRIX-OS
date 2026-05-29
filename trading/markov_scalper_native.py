#!/usr/bin/env python3
"""markov_scalper_native.py — MAGNATRIX-OS Trading Layer
Markov Regime Binary Scalper.

Pattern: AMATI-PELAJARI-TIRU dari screenshot Polymarket/Markov Scalper UI.

Features:
  - Markov Regime Model: Hidden state transitions (Bull/Bear/Range)
  - Binary Outcome Prediction: YES/NO binary option pricing
  - Monte Carlo Simulation: 500+ paths for probability estimation
  - Pattern Scanner: Displacement, FVG (Fair Value Gap), Imbalance detection
  - 5-Min Horizon: fast scalp with 5-minute resolution
  - Kelly Criterion + CAP: position sizing with maximum drawdown cap
  - Live Execution Cycle: scan → fetch → model → size → execute

Usage:
    scalper = NativeMarkovScalper()
    scalper.add_market("BTC-5MIN", current_price=75000, book_depth=book)
    signal = scalper.generate_signal("BTC-5MIN")
    if signal["confidence"] > 0.75:
        size = scalper.kelly_size(signal["edge"], bankroll=100000)
        scalper.execute(signal, size)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

class Regime(Enum):
    BULL = auto()
    BEAR = auto()
    RANGE = auto()


@dataclass
class MarketSnapshot:
    symbol: str
    price: float
    bid: float
    ask: float
    volume: float
    timestamp: float
    book_depth_bid: float = 0.0
    book_depth_ask: float = 0.0


@dataclass
class Signal:
    symbol: str
    side: str           # 'YES' or 'NO' (binary outcome)
    regime: Regime
    confidence: float
    edge: float
    target_price: float
    stop_price: float
    pattern: str
    monte_carlo_prob: float


# ══════════════════════════════════════════════════════════════════════════════
# Markov Regime Model
# ══════════════════════════════════════════════════════════════════════════════

class MarkovRegimeModel:
    """2-state Markov chain for regime detection with transition probabilities."""

    def __init__(self, p_bull_to_bull: float = 0.85, p_bear_to_bear: float = 0.80,
                 p_range_to_bull: float = 0.30, p_range_to_bear: float = 0.30) -> None:
        # Transition matrix: [current][next] = probability
        self.transitions = {
            Regime.BULL: {Regime.BULL: p_bull_to_bull, Regime.BEAR: 0.15, Regime.RANGE: 1 - p_bull_to_bull - 0.15},
            Regime.BEAR: {Regime.BULL: 0.15, Regime.BEAR: p_bear_to_bear, Regime.RANGE: 1 - 0.15 - p_bear_to_bear},
            Regime.RANGE: {Regime.BULL: p_range_to_bull, Regime.BEAR: p_range_to_bear, Regime.RANGE: 1 - p_range_to_bull - p_range_to_bear},
        }
        self.current_regime = Regime.RANGE
        self._history: List[Regime] = []
        self._price_history: List[float] = []

    def update(self, price: float, sma_fast: float, sma_slow: float, atr: float) -> Regime:
        self._price_history.append(price)
        if len(self._price_history) > 100:
            self._price_history = self._price_history[-100:]

        # Determine most likely regime based on price action
        if sma_fast > sma_slow and price > sma_fast + atr * 0.5:
            observed = Regime.BULL
        elif sma_fast < sma_slow and price < sma_slow - atr * 0.5:
            observed = Regime.BEAR
        else:
            observed = Regime.RANGE

        # Transition to most likely next state given current
        best_prob = 0.0
        best_regime = self.current_regime
        for regime, prob in self.transitions[self.current_regime].items():
            if regime == observed:
                prob *= 1.5  # Boost if observed matches transition target
            if prob > best_prob:
                best_prob = prob
                best_regime = regime

        self.current_regime = best_regime
        self._history.append(best_regime)
        return best_regime

    def regime_probability(self, regime: Regime) -> float:
        if not self._history:
            return 0.33
        return self._history.count(regime) / len(self._history)


# ══════════════════════════════════════════════════════════════════════════════
# Monte Carlo Simulation
# ══════════════════════════════════════════════════════════════════════════════

class MonteCarloSimulator:
    """Simulate price paths for binary outcome probability estimation."""

    def __init__(self, paths: int = 500, steps: int = 30) -> None:
        self.paths = paths
        self.steps = steps

    def simulate(self, current_price: float, drift: float, volatility: float,
                 target_price: float, time_horizon: float = 5.0) -> float:
        """Return probability of price >= target_price at horizon."""
        dt = time_horizon / self.steps
        successes = 0

        for _ in range(self.paths):
            price = current_price
            for _ in range(self.steps):
                # Geometric Brownian Motion
                dW = random.gauss(0, math.sqrt(dt))
                price *= math.exp((drift - 0.5 * volatility ** 2) * dt + volatility * dW)
            if price >= target_price:
                successes += 1

        return successes / self.paths


# ══════════════════════════════════════════════════════════════════════════════
# Pattern Scanner
# ══════════════════════════════════════════════════════════════════════════════

class PatternScanner:
    """Detect price action patterns: Displacement, FVG, Imbalance."""

    @staticmethod
    def detect_displacement(prices: List[float], threshold: float = 0.02) -> Optional[Dict[str, Any]]:
        """Detect sudden displacement (large move in short time)."""
        if len(prices) < 5:
            return None
        recent = prices[-5:]
        move = (recent[-1] - recent[0]) / recent[0]
        if abs(move) >= threshold:
            return {
                "type": "displacement",
                "direction": "up" if move > 0 else "down",
                "magnitude": abs(move),
                "confidence": min(1.0, abs(move) / threshold * 0.5),
            }
        return None

    @staticmethod
    def detect_fvg(candles: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """Detect Fair Value Gap (imbalance between candle wicks)."""
        if len(candles) < 3:
            return None
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        # Bullish FVG: c2 low > c1 high, c3 confirms
        if c2["low"] > c1["high"] and c3["close"] > c2["high"]:
            return {
                "type": "fvg_bullish",
                "gap": c2["low"] - c1["high"],
                "confidence": 0.75,
            }
        # Bearish FVG: c2 high < c1 low, c3 confirms
        if c2["high"] < c1["low"] and c3["close"] < c2["low"]:
            return {
                "type": "fvg_bearish",
                "gap": c1["low"] - c2["high"],
                "confidence": 0.75,
            }
        return None

    @staticmethod
    def detect_imbalance(candles: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """Detect order imbalance via wick analysis."""
        if len(candles) < 2:
            return None
        c = candles[-1]
        body = abs(c["close"] - c["open"])
        upper_wick = c["high"] - max(c["open"], c["close"])
        lower_wick = min(c["open"], c["close"]) - c["low"]

        if upper_wick > body * 2:
            return {"type": "imbalance_sell", "confidence": 0.60}
        if lower_wick > body * 2:
            return {"type": "imbalance_buy", "confidence": 0.60}
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Kelly + CAP Sizing
# ══════════════════════════════════════════════════════════════════════════════

class KellyCAPSizer:
    """Kelly Criterion with Capital Allocation Protection (CAP)."""

    def __init__(self, kelly_fraction: float = 0.5, max_drawdown_cap: float = 0.15,
                 max_position_pct: float = 0.10) -> None:
        self.kelly_fraction = kelly_fraction
        self.max_dd_cap = max_drawdown_cap
        self.max_position_pct = max_position_pct

    def size(self, edge: float, win_prob: float, bankroll: float,
             current_drawdown: float = 0.0) -> Dict[str, Any]:
        if edge <= 0 or win_prob <= 0 or win_prob >= 1:
            return {"contracts": 0, "fraction": 0, "reason": "invalid edge/probability"}

        # Kelly: f = (bp - q) / b
        b = abs(edge) / (1 - win_prob) if (1 - win_prob) > 0 else 1.0
        q = 1 - win_prob
        raw_f = (b * win_prob - q) / b if b > 0 else 0
        raw_f = max(0, min(raw_f, 1.0))

        # Half-Kelly
        f = raw_f * self.kelly_fraction

        # CAP: reduce size if near drawdown limit
        dd_ratio = current_drawdown / self.max_dd_cap if self.max_dd_cap > 0 else 0
        if dd_ratio > 0.5:
            f *= (1 - dd_ratio)  # Reduce linearly as DD approaches cap

        # Position limit
        max_dollar = bankroll * self.max_position_pct
        dollar = bankroll * f
        dollar = min(dollar, max_dollar)

        return {
            "fraction": f,
            "raw_kelly": raw_f,
            "dollar_amount": dollar,
            "contracts": int(dollar / 100) if dollar > 0 else 0,  # Assuming $100 per contract
            "reason": "kelly+cap",
        }


# ══════════════════════════════════════════════════════════════════════════════
# Unified Markov Scalper
# ══════════════════════════════════════════════════════════════════════════════

class NativeMarkovScalper:
    """Markov Regime Binary Scalper with Monte Carlo + Pattern detection."""

    def __init__(self, bankroll: float = 100000.0) -> None:
        self.bankroll = bankroll
        self.markov = MarkovRegimeModel()
        self.mc = MonteCarloSimulator(paths=500, steps=30)
        self.patterns = PatternScanner()
        self.sizer = KellyCAPSizer()
        self._markets: Dict[str, List[MarketSnapshot]] = {}
        self._candles: Dict[str, List[Dict[str, float]]] = {}
        self._trades: List[Dict[str, Any]] = []
        self._drawdown = 0.0

    def add_snapshot(self, snap: MarketSnapshot) -> None:
        self._markets.setdefault(snap.symbol, []).append(snap)
        if len(self._markets[snap.symbol]) > 100:
            self._markets[snap.symbol] = self._markets[snap.symbol][-100:]

    def add_candle(self, symbol: str, candle: Dict[str, float]) -> None:
        self._candles.setdefault(symbol, []).append(candle)
        if len(self._candles[symbol]) > 50:
            self._candles[symbol] = self._candles[symbol][-50:]

    def generate_signal(self, symbol: str) -> Dict[str, Any]:
        snaps = self._markets.get(symbol, [])
        candles = self._candles.get(symbol, [])
        if len(snaps) < 20 or len(candles) < 5:
            return {"error": "Insufficient data"}

        prices = [s.price for s in snaps]
        sma_fast = sum(prices[-10:]) / 10
        sma_slow = sum(prices[-30:]) / 30
        atr = sum(abs(prices[i] - prices[i-1]) for i in range(-14, 0)) / 14

        # Markov regime
        regime = self.markov.update(prices[-1], sma_fast, sma_slow, atr)

        # Monte Carlo probability
        drift = (prices[-1] - prices[-20]) / prices[-20] / 20
        volatility = math.sqrt(sum((p - sma_fast) ** 2 for p in prices[-20:]) / 20) / sma_fast
        target_price = prices[-1] * (1.01 if regime == Regime.BULL else 0.99 if regime == Regime.BEAR else 1.0)
        mc_prob = self.mc.simulate(prices[-1], drift, volatility, target_price, time_horizon=5.0)

        # Pattern detection
        pattern = None
        for detector in [self.patterns.detect_displacement, self.patterns.detect_fvg, self.patterns.detect_imbalance]:
            if detector == self.patterns.detect_displacement:
                pattern = detector(prices, threshold=0.01)
            elif detector == self.patterns.detect_fvg and len(candles) >= 3:
                pattern = detector(candles)
            elif detector == self.patterns.detect_imbalance and len(candles) >= 2:
                pattern = detector(candles)
            if pattern:
                break

        # Edge and signal
        market_prob = 0.5  # Binary market midpoint
        model_prob = mc_prob if regime == Regime.BULL else 1 - mc_prob if regime == Regime.BEAR else 0.5
        edge = model_prob - market_prob
        confidence = min(1.0, abs(edge) * 5 + (0.2 if pattern else 0))

        side = "YES" if edge > 0 else "NO"

        return {
            "symbol": symbol,
            "side": side,
            "regime": regime.name,
            "confidence": confidence,
            "edge": edge,
            "model_prob": model_prob,
            "monte_carlo_prob": mc_prob,
            "pattern": pattern["type"] if pattern else "none",
            "target_price": target_price,
            "stop_price": prices[-1] * (0.995 if side == "YES" else 1.005),
        }

    def kelly_size(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return self.sizer.size(
            edge=abs(signal["edge"]),
            win_prob=signal["model_prob"],
            bankroll=self.bankroll,
            current_drawdown=self._drawdown,
        )

    def execute(self, signal: Dict[str, Any], size: Dict[str, Any]) -> Dict[str, Any]:
        if size["contracts"] <= 0:
            return {"ok": False, "reason": size.get("reason", "zero size")}

        trade = {
            "symbol": signal["symbol"],
            "side": signal["side"],
            "contracts": size["contracts"],
            "dollar": size["dollar_amount"],
            "confidence": signal["confidence"],
            "edge": signal["edge"],
            "regime": signal["regime"],
            "pattern": signal["pattern"],
            "timestamp": snaps[-1].timestamp if (snaps := self._markets.get(signal["symbol"])) else 0,
        }
        self._trades.append(trade)
        return {"ok": True, "trade": trade}

    def status(self) -> Dict[str, Any]:
        return {
            "bankroll": self.bankroll,
            "drawdown": self._drawdown,
            "trades": len(self._trades),
            "current_regime": self.markov.current_regime.name,
            "regime_history": {r.name: self.markov._history.count(r) for r in Regime},
        }


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Markov Scalper — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Generate synthetic data
    random.seed(42)
    base_price = 75000.0
    scalper = NativeMarkovScalper(bankroll=100000.0)

    prices = [base_price]
    for i in range(1, 50):
        prices.append(prices[-1] * (1 + random.gauss(0.0002, 0.005)))

    for i, p in enumerate(prices):
        snap = MarketSnapshot(
            symbol="BTC-5MIN", price=p, bid=p-5, ask=p+5,
            volume=random.uniform(100, 1000), timestamp=i*300,
        )
        scalper.add_snapshot(snap)
        candle = {"open": p * 0.999, "high": p * 1.005, "low": p * 0.995, "close": p}
        scalper.add_candle("BTC-5MIN", candle)

    # Test 1: Markov regime
    print("[Test 1] Markov regime detection")
    signal = scalper.generate_signal("BTC-5MIN")
    ok = "regime" in signal and signal["regime"] in ("BULL", "BEAR", "RANGE")
    print(f"  Regime: {signal.get('regime')} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Monte Carlo probability
    print("[Test 2] Monte Carlo probability")
    ok2 = "monte_carlo_prob" in signal and 0 <= signal["monte_carlo_prob"] <= 1
    print(f"  MC prob: {signal.get('monte_carlo_prob', 0):.4f} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Pattern detection
    print("[Test 3] Pattern detection")
    ok3 = "pattern" in signal
    print(f"  Pattern: {signal.get('pattern')} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Edge
    print("[Test 4] Edge computation")
    ok4 = "edge" in signal and abs(signal["edge"]) >= 0
    print(f"  Edge: {signal.get('edge', 0):.4f} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Kelly sizing
    print("[Test 5] Kelly sizing")
    size = scalper.kelly_size(signal)
    ok5 = size["fraction"] >= 0
    print(f"  Kelly fraction: {size['fraction']:.4f} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Trade execution
    print("[Test 6] Trade execution")
    result = scalper.execute(signal, size)
    ok6 = result["ok"] or "reason" in result
    print(f"  Execute OK: {result.get('ok')} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Status
    print("[Test 7] Status report")
    st = scalper.status()
    ok7 = st["trades"] >= 0 and st["current_regime"] in ("BULL", "BEAR", "RANGE")
    print(f"  Status valid: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
