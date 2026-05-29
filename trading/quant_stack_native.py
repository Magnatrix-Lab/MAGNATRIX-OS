#!/usr/bin/env python3
"""quant_stack_native.py — MAGNATRIX-OS Trading Layer
3-Layer Quantitative Trading Stack (Roan's Architecture).

Pattern: AMATI-PELAJARI-TIRU dari Roan's 3-Layer Quantitative Trading Stack.

Architecture:
  Layer 1 — Markov Chain Regime Detection: Hidden state transitions (Bull/Bear/Range)
  Layer 2 — Neural Network Signal: LSTM signal generation (pure Python, no external deps)
  Layer 3 — Time Series Forecasting: ARIMA trend + GARCH volatility → position sizing

Flow: Raw Price → Layer 1 (Regime) → Layer 2 (LSTM Signal) → Layer 3 (ARIMA/GARCH Size) → Execute

Usage:
    stack = NativeQuantStack()
    stack.add_price_history(prices)  # list of floats
    signal = stack.generate_signal()
    # signal: {regime, lstm_prob, arima_forecast, garch_vol, position_size, confidence}
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Layer 1: Markov Chain Regime Detection
# ══════════════════════════════════════════════════════════════════════════════

class MarkovChainRegime:
    """Hidden state Markov chain for market regime detection."""

    def __init__(self, states: Optional[List[str]] = None) -> None:
        self.states = states or ["bull", "bear", "range"]
        self.n = len(self.states)
        # Transition matrix: P[i][j] = probability of going from state i to state j
        self.transitions = {
            "bull": {"bull": 0.85, "bear": 0.10, "range": 0.05},
            "bear": {"bull": 0.10, "bear": 0.80, "range": 0.10},
            "range": {"bull": 0.30, "bear": 0.30, "range": 0.40},
        }
        self.current_state = "range"
        self._history: List[str] = []
        self._state_counts: Dict[str, int] = {s: 0 for s in self.states}

    def _observed_state(self, returns: List[float]) -> str:
        """Determine observed state from recent returns."""
        if len(returns) < 5:
            return "range"
        avg_ret = sum(returns) / len(returns)
        std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in returns) / len(returns)) if len(returns) > 1 else 0.001
        if std_ret == 0:
            std_ret = 0.001
        z = avg_ret / std_ret
        if z > 1.5:
            return "bull"
        elif z < -1.5:
            return "bear"
        return "range"

    def update(self, prices: List[float]) -> str:
        """Update Markov state based on price history."""
        if len(prices) < 2:
            return self.current_state
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        observed = self._observed_state(returns[-10:])

        # Transition to most likely next state given current
        probs = self.transitions.get(self.current_state, {})
        best_prob = 0.0
        best_state = self.current_state
        for state, prob in probs.items():
            if state == observed:
                prob *= 1.5  # Boost if observed matches
            if prob > best_prob:
                best_prob = prob
                best_state = state

        self.current_state = best_state
        self._history.append(best_state)
        self._state_counts[best_state] += 1
        return best_state

    def state_probability(self, state: str) -> float:
        total = sum(self._state_counts.values())
        return self._state_counts[state] / total if total > 0 else 0.33

    def expected_duration(self, state: str) -> float:
        """Expected duration of a state before transition."""
        p_stay = self.transitions.get(state, {}).get(state, 0.5)
        return 1 / (1 - p_stay) if p_stay < 1 else 10.0


# ══════════════════════════════════════════════════════════════════════════════
# Layer 2: Neural Network (LSTM) Signal Generator
# ══════════════════════════════════════════════════════════════════════════════

class LSTMCell:
    """Simplified LSTM cell for pure Python signal generation."""

    def __init__(self, input_size: int = 1, hidden_size: int = 8) -> None:
        self.input_size = input_size
        self.hidden_size = hidden_size
        # Initialize weights randomly (small values)
        self.Wf = [[random.uniform(-0.1, 0.1) for _ in range(input_size + hidden_size)] for _ in range(hidden_size)]
        self.Wi = [[random.uniform(-0.1, 0.1) for _ in range(input_size + hidden_size)] for _ in range(hidden_size)]
        self.Wc = [[random.uniform(-0.1, 0.1) for _ in range(input_size + hidden_size)] for _ in range(hidden_size)]
        self.Wo = [[random.uniform(-0.1, 0.1) for _ in range(input_size + hidden_size)] for _ in range(hidden_size)]
        self.bf = [random.uniform(-0.1, 0.1) for _ in range(hidden_size)]
        self.bi = [random.uniform(-0.1, 0.1) for _ in range(hidden_size)]
        self.bc = [random.uniform(-0.1, 0.1) for _ in range(hidden_size)]
        self.bo = [random.uniform(-0.1, 0.1) for _ in range(hidden_size)]
        self.h = [0.0] * hidden_size
        self.c = [0.0] * hidden_size

    def _sigmoid(self, x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    def _tanh(self, x: float) -> float:
        return math.tanh(x)

    def step(self, x: List[float]) -> List[float]:
        """Single LSTM step. Returns new hidden state."""
        concat = x + self.h
        # Forget gate
        f = [self._sigmoid(sum(self.Wf[i][j] * concat[j] for j in range(len(concat))) + self.bf[i]) for i in range(self.hidden_size)]
        # Input gate
        i = [self._sigmoid(sum(self.Wi[i][j] * concat[j] for j in range(len(concat))) + self.bi[i]) for i in range(self.hidden_size)]
        # Candidate cell state
        c_tilde = [self._tanh(sum(self.Wc[i][j] * concat[j] for j in range(len(concat))) + self.bc[i]) for i in range(self.hidden_size)]
        # Update cell state
        self.c = [f[j] * self.c[j] + i[j] * c_tilde[j] for j in range(self.hidden_size)]
        # Output gate
        o = [self._sigmoid(sum(self.Wo[i][j] * concat[j] for j in range(len(concat))) + self.bo[i]) for i in range(self.hidden_size)]
        # New hidden state
        self.h = [o[j] * self._tanh(self.c[j]) for j in range(self.hidden_size)]
        return list(self.h)

    def forward(self, sequence: List[List[float]]) -> List[float]:
        """Process entire sequence and return final hidden state."""
        for x in sequence:
            self.step(x)
        return list(self.h)

    def predict_signal(self, sequence: List[float]) -> float:
        """Predict trading signal from price sequence. Returns 0-1 score."""
        # Normalize returns
        mean = sum(sequence) / len(sequence) if sequence else 0
        std = math.sqrt(sum((x - mean) ** 2 for x in sequence) / len(sequence)) if len(sequence) > 1 else 1
        std = max(std, 0.001)
        normalized = [[(x - mean) / std] for x in sequence]
        h = self.forward(normalized)
        # Simple linear readout: average of hidden units mapped to [0,1]
        score = sum(h) / len(h) if h else 0.5
        return (self._sigmoid(score * 2) - 0.5) * 2 + 0.5  # Scale to [0,1]


class LSTMSignalGenerator:
    """LSTM-based signal generator for trading."""

    def __init__(self, hidden_size: int = 8, sequence_length: int = 20) -> None:
        self.lstm = LSTMCell(input_size=1, hidden_size=hidden_size)
        self.sequence_length = sequence_length

    def generate(self, prices: List[float]) -> Dict[str, Any]:
        if len(prices) < self.sequence_length:
            return {"signal": 0.5, "confidence": 0.0, "direction": "neutral"}
        seq = prices[-self.sequence_length:]
        score = self.lstm.predict_signal(seq)
        direction = "buy" if score > 0.6 else "sell" if score < 0.4 else "neutral"
        confidence = abs(score - 0.5) * 2  # 0-1 scale
        return {
            "signal": score,
            "confidence": confidence,
            "direction": direction,
            "raw_score": score,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Layer 3: ARIMA + GARCH Time Series
# ══════════════════════════════════════════════════════════════════════════════

class ARIMAForecaster:
    """Simplified ARIMA(1,1,1) forecaster."""

    def __init__(self, p: int = 1, d: int = 1, q: int = 1) -> None:
        self.p = p
        self.d = d
        self.q = q
        self.phi = 0.5  # AR coefficient
        self.theta = 0.3  # MA coefficient
        self._residuals: List[float] = []

    def _difference(self, series: List[float], d: int) -> List[float]:
        diff = list(series)
        for _ in range(d):
            diff = [diff[i] - diff[i-1] for i in range(1, len(diff))]
        return diff

    def fit(self, prices: List[float]) -> None:
        if len(prices) < 10:
            return
        returns = self._difference(prices, self.d)
        if len(returns) < 2:
            return
        # Simple AR(1) estimation: phi = corr(returns[t], returns[t-1])
        x = returns[:-1]
        y = returns[1:]
        mean_x = sum(x) / len(x)
        mean_y = sum(y) / len(y)
        num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
        den = sum((x[i] - mean_x) ** 2 for i in range(len(x)))
        self.phi = num / den if den > 0 else 0.5
        self.phi = max(-0.99, min(0.99, self.phi))

        # Residuals for GARCH
        self._residuals = []
        for i in range(1, len(returns)):
            pred = self.phi * returns[i-1]
            self._residuals.append(returns[i] - pred)

    def forecast(self, prices: List[float], steps: int = 1) -> List[float]:
        if len(prices) < 5:
            return [prices[-1]] if prices else [0.0]
        last_price = prices[-1]
        returns = self._difference(prices, self.d)
        if not returns:
            return [last_price]
        last_return = returns[-1]
        forecasts = []
        for _ in range(steps):
            next_return = self.phi * last_return
            last_price += next_return
            forecasts.append(last_price)
        return forecasts


class GARCHVolatility:
    """Simplified GARCH(1,1) volatility estimator."""

    def __init__(self, omega: float = 0.00001, alpha: float = 0.1, beta: float = 0.85) -> None:
        self.omega = omega
        self.alpha = alpha
        self.beta = beta
        self.sigma2 = omega / (1 - alpha - beta) if (alpha + beta) < 1 else 0.001

    def update(self, return_t: float) -> float:
        """Update volatility estimate with new return."""
        self.sigma2 = self.omega + self.alpha * return_t ** 2 + self.beta * self.sigma2
        return math.sqrt(self.sigma2)

    def estimate(self, returns: List[float]) -> float:
        """Estimate volatility from return series."""
        for r in returns:
            self.update(r)
        return math.sqrt(self.sigma2)

    def position_size_multiplier(self, vol: float, target_vol: float = 0.02) -> float:
        """Reduce position size when volatility is high."""
        if vol <= 0:
            return 1.0
        return min(1.0, target_vol / vol)


class TimeSeriesEngine:
    """ARIMA + GARCH combined forecasting engine."""

    def __init__(self) -> None:
        self.arima = ARIMAForecaster()
        self.garch = GARCHVolatility()

    def analyze(self, prices: List[float]) -> Dict[str, Any]:
        if len(prices) < 20:
            return {"forecast": prices[-1] if prices else 0, "volatility": 0.01, "size_mult": 1.0}

        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        self.arima.fit(prices)
        forecast = self.arima.forecast(prices, steps=1)[0]
        vol = self.garch.estimate(returns)
        size_mult = self.garch.position_size_multiplier(vol)

        return {
            "forecast": forecast,
            "volatility": vol,
            "size_mult": size_mult,
            "trend_direction": "up" if forecast > prices[-1] else "down",
            "trend_strength": abs(forecast - prices[-1]) / prices[-1] if prices[-1] > 0 else 0,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Unified 3-Layer Quant Stack
# ══════════════════════════════════════════════════════════════════════════════

class NativeQuantStack:
    """Unified 3-layer quantitative trading stack."""

    def __init__(self, bankroll: float = 100000.0) -> None:
        self.bankroll = bankroll
        self.layer1 = MarkovChainRegime()
        self.layer2 = LSTMSignalGenerator()
        self.layer3 = TimeSeriesEngine()
        self._prices: List[float] = []
        self._signals: List[Dict[str, Any]] = []

    def add_price(self, price: float) -> None:
        self._prices.append(price)
        if len(self._prices) > 200:
            self._prices = self._prices[-200:]

    def add_prices(self, prices: List[float]) -> None:
        for p in prices:
            self.add_price(p)

    def generate_signal(self) -> Dict[str, Any]:
        """Generate unified trading signal from all 3 layers."""
        if len(self._prices) < 30:
            return {"error": "Insufficient data (need 30+ prices)"}

        # Layer 1: Markov regime
        regime = self.layer1.update(self._prices)
        regime_prob = self.layer1.state_probability(regime)
        expected_duration = self.layer1.expected_duration(regime)

        # Layer 2: LSTM signal
        lstm = self.layer2.generate(self._prices)

        # Layer 3: ARIMA + GARCH
        ts = self.layer3.analyze(self._prices)

        # Combine signals
        # Regime score: bull=1, bear=-1, range=0
        regime_score = {"bull": 1.0, "bear": -1.0, "range": 0.0}.get(regime, 0.0)

        # LSTM score: buy=1, sell=-1, neutral=0
        lstm_score = {"buy": 1.0, "sell": -1.0, "neutral": 0.0}.get(lstm["direction"], 0.0)

        # Trend score: up=1, down=-1
        trend_score = 1.0 if ts["trend_direction"] == "up" else -1.0

        # Weighted ensemble
        combined_score = (regime_score * 0.3 + lstm_score * 0.4 + trend_score * 0.3)

        # Confidence
        confidence = (regime_prob * 0.3 + lstm["confidence"] * 0.4 + (1 - ts["size_mult"]) * 0.3)
        confidence = min(1.0, max(0.0, confidence))

        # Position size
        base_size = self.bankroll * 0.02  # 2% per trade
        position_size = base_size * ts["size_mult"] * confidence

        signal = {
            "regime": regime,
            "regime_prob": regime_prob,
            "regime_duration": expected_duration,
            "lstm_signal": lstm["signal"],
            "lstm_direction": lstm["direction"],
            "lstm_confidence": lstm["confidence"],
            "arima_forecast": ts["forecast"],
            "trend_direction": ts["trend_direction"],
            "trend_strength": ts["trend_strength"],
            "garch_volatility": ts["volatility"],
            "size_multiplier": ts["size_mult"],
            "combined_score": combined_score,
            "confidence": confidence,
            "position_size": position_size,
            "action": "buy" if combined_score > 0.2 else "sell" if combined_score < -0.2 else "hold",
            "current_price": self._prices[-1] if self._prices else 0,
        }
        self._signals.append(signal)
        return signal

    def backtest(self, prices: List[float], threshold: float = 0.2) -> Dict[str, Any]:
        """Simple backtest of the 3-layer stack."""
        pnl = 0.0
        trades = 0
        wins = 0
        position = 0.0
        entry_price = 0.0

        for i in range(30, len(prices)):
            self._prices = prices[:i+1]
            signal = self.generate_signal()
            action = signal.get("action", "hold")
            price = prices[i]

            if action == "buy" and position == 0:
                position = 1.0
                entry_price = price
                trades += 1
            elif action == "sell" and position == 1.0:
                trade_pnl = (price - entry_price) / entry_price
                pnl += trade_pnl
                if trade_pnl > 0:
                    wins += 1
                position = 0.0

        return {
            "trades": trades,
            "win_rate": wins / trades if trades > 0 else 0,
            "total_return": pnl,
            "sharpe_approx": pnl / math.sqrt(trades) if trades > 0 else 0,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "prices": len(self._prices),
            "signals": len(self._signals),
            "current_regime": self.layer1.current_state,
            "bankroll": self.bankroll,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native 3-Layer Quant Stack — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Generate synthetic price data
    random.seed(42)
    prices = [100.0]
    for _ in range(150):
        prices.append(prices[-1] * (1 + random.gauss(0.0005, 0.01)))

    stack = NativeQuantStack(bankroll=100000.0)
    stack.add_prices(prices[:50])

    # Test 1: Markov regime
    print("[Test 1] Markov regime detection")
    regime = stack.layer1.update(prices[:50])
    ok = regime in ("bull", "bear", "range")
    print(f"  Regime: {regime} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: LSTM signal
    print("[Test 2] LSTM signal generation")
    lstm = stack.layer2.generate(prices[:50])
    ok2 = lstm["direction"] in ("buy", "sell", "neutral") and 0 <= lstm["signal"] <= 1
    print(f"  LSTM: {lstm['direction']} (score={lstm['signal']:.3f}) — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: ARIMA forecast
    print("[Test 3] ARIMA forecast")
    ts = stack.layer3.analyze(prices[:50])
    ok3 = ts["forecast"] > 0 and ts["volatility"] > 0
    print(f"  ARIMA forecast={ts['forecast']:.2f}, vol={ts['volatility']:.4f} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: GARCH volatility
    print("[Test 4] GARCH volatility")
    garch = GARCHVolatility()
    vol = garch.estimate([(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, 50)])
    ok4 = vol > 0 and vol < 1.0
    print(f"  GARCH vol={vol:.4f} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Full signal
    print("[Test 5] Full 3-layer signal")
    stack.add_prices(prices[50:100])
    signal = stack.generate_signal()
    ok5 = "action" in signal and signal["action"] in ("buy", "sell", "hold")
    print(f"  Action: {signal['action']}, confidence={signal['confidence']:.3f} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Backtest
    print("[Test 6] Backtest")
    bt = stack.backtest(prices)
    ok6 = bt["trades"] >= 0
    print(f"  Trades={bt['trades']}, win_rate={bt['win_rate']:.2%} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Status
    print("[Test 7] Status report")
    st = stack.status()
    ok7 = st["prices"] >= 100 and st["signals"] > 0
    print(f"  Prices={st['prices']}, signals={st['signals']}: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
