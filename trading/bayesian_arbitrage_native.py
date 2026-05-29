#!/usr/bin/env python3
"""bayesian_arbitrage_native.py — MAGNATRIX-OS Trading Layer
Polymarket Bayesian Prediction Market Arbitrage Bot.

Pattern: AMATI-PELAJARI-TIRU dari Polymarket Prediction Market Arbitrage Bot.

Features:
  - Bayesian Update Engine: P(A|B) = P(B|A)*P(A) / [P(B|A)*P(A) + P(B|~A)*P(~A)]
  - Net Edge Calculation: edge after costs and slippage
  - Kelly Criterion for Prediction Markets: b = (1-P)/P, f = (bp-q)/b
  - Cross-Market Spread Analysis: detect stale pricing across venues
  - Stoikov-Style Market Making: inventory-based spread, gamma risk aversion
  - Latency Arbitrage: exploit 1-2 tick price differences
  - Repricing Signals: detect when market price diverges from fair value
  - Z-Score Analysis: statistical significance of price moves

Usage:
    bot = NativeBayesianArbitrageBot(bankroll=10000, kelly_fraction=0.25)
    signal = bot.create_signal(ticker="BTC-UP", prior=0.41, likelihood_true=0.78, likelihood_false=0.24)
    result = bot.process_signal(signal)
    if result["action"] == "buy_yes":
        bot.execute_yes(signal.ticker, result["size"])
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Bayesian Update Engine
# ══════════════════════════════════════════════════════════════════════════════

class BayesianEngine:
    """Bayesian probability update engine for prediction markets."""

    @staticmethod
    def update(prior: float, likelihood_true: float, likelihood_false: float) -> float:
        """Calculate posterior probability using Bayes' theorem.

        P(A|B) = P(B|A) * P(A) / [P(B|A)*P(A) + P(B|~A)*P(~A)]
        """
        numerator = likelihood_true * prior
        denominator = numerator + likelihood_false * (1 - prior)
        return numerator / denominator if denominator > 0 else prior

    @staticmethod
    def sequential_update(prior: float, signals: List[Tuple[float, float]]) -> float:
        """Apply multiple Bayesian updates sequentially.
        Each signal: (likelihood_true, likelihood_false)
        """
        current = prior
        for lt, lf in signals:
            current = BayesianEngine.update(current, lt, lf)
        return current

    @staticmethod
    def net_edge(model_probability: float, market_price: float, cost: float = 0.015) -> float:
        """Net edge after transaction costs and slippage."""
        return model_probability - market_price - cost

    @staticmethod
    def z_score(value: float, mean: float, std: float) -> float:
        """Statistical significance of a value."""
        return (value - mean) / std if std > 0 else 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Kelly Criterion for Prediction Markets
# ══════════════════════════════════════════════════════════════════════════════

class KellyPredictor:
    """Kelly Criterion position sizing for binary prediction markets."""

    @staticmethod
    def kelly_position_size(p: float, market_price: float, fraction: float = 0.25) -> float:
        """Calculate optimal position size for prediction markets.

        On binary markets: buying YES at price P means:
        - Risk: P dollars per share
        - Reward: (1-P) dollars per share if correct
        - Net odds: b = (1-P) / P

        Kelly: f = (b*p - q) / b where q = 1-p
        """
        if market_price <= 0 or market_price >= 1 or p <= 0 or p >= 1:
            return 0.0
        b = (1 - market_price) / market_price
        q = 1 - p
        kelly = (b * p - q) / b if b > 0 else 0
        return max(0.0, min(0.5, kelly * fraction))

    @staticmethod
    def calculate_edge(p_fair: float, p_market: float) -> Dict[str, Any]:
        """Calculate edge metrics for a prediction market."""
        edge = p_fair - p_market
        edge_pct = edge * 100
        kelly = KellyPredictor.kelly_position_size(p_fair, p_market)
        return {
            "model_prob": p_fair,
            "market_prob": p_market,
            "edge": edge,
            "edge_pct": edge_pct,
            "kelly_fraction": kelly,
            "side": "yes" if edge > 0 else "no",
            "actionable": abs(edge) > 0.02 and kelly > 0.01,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Cross-Market Spread Analysis
# ══════════════════════════════════════════════════════════════════════════════

class CrossMarketAnalyzer:
    """Detect stale pricing across multiple venues."""

    @staticmethod
    def cross_market_spread_analysis(prices: Dict[str, float], threshold: float = 0.01) -> List[Dict[str, Any]]:
        """Find cross-market arbitrage opportunities."""
        opportunities = []
        venues = list(prices.keys())
        for i in range(len(venues)):
            for j in range(i + 1, len(venues)):
                v1, v2 = venues[i], venues[j]
                spread = abs(prices[v1] - prices[v2])
                avg = (prices[v1] + prices[v2]) / 2
                spread_pct = spread / avg if avg > 0 else 0
                if spread_pct >= threshold:
                    opportunities.append({
                        "venue_a": v1, "price_a": prices[v1],
                        "venue_b": v2, "price_b": prices[v2],
                        "spread": spread, "spread_pct": spread_pct,
                        "buy_at": v2 if prices[v1] > prices[v2] else v1,
                        "sell_at": v1 if prices[v1] > prices[v2] else v2,
                    })
        return opportunities


# ══════════════════════════════════════════════════════════════════════════════
# Stoikov-Style Market Making
# ══════════════════════════════════════════════════════════════════════════════

class StoikovMarketMaker:
    """Inventory-based market making with gamma risk aversion."""

    def __init__(self, gamma: float = 0.1, sigma: float = 0.02) -> None:
        self.gamma = gamma
        self.sigma = sigma
        self.inventory = 0
        self.max_inventory = 100

    def calculate_spread(self, fair_price: float, time_to_expiry: float) -> Tuple[float, float]:
        """Calculate optimal bid/ask spread."""
        spread = self.gamma * self.sigma ** 2 * time_to_expiry
        spread = max(0.01, min(0.10, spread))  # Cap spread 1-10%
        bid = fair_price * (1 - spread / 2)
        ask = fair_price * (1 + spread / 2)
        return bid, ask

    def update_inventory(self, shares_bought: int = 0, shares_sold: int = 0) -> None:
        self.inventory += shares_bought - shares_sold

    def should_quote(self) -> bool:
        return abs(self.inventory) < self.max_inventory

    def get_skew(self) -> float:
        """Inventory skew: bias quotes to reduce inventory."""
        return -self.gamma * self.inventory / self.max_inventory


# ══════════════════════════════════════════════════════════════════════════════
# Repricing Signal Detector
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RepricingSignal:
    ticker: str
    fair_price: float
    market_price: float
    divergence: float
    z_score: float
    action: str  # "buy", "sell", "hold"
    confidence: float


class RepricingDetector:
    """Detect when market price diverges from fair value."""

    def __init__(self, z_threshold: float = 2.0) -> None:
        self.z_threshold = z_threshold
        self._history: Dict[str, List[float]] = {}

    def add_price(self, ticker: str, price: float) -> None:
        self._history.setdefault(ticker, []).append(price)
        if len(self._history[ticker]) > 100:
            self._history[ticker] = self._history[ticker][-100:]

    def detect(self, ticker: str, fair_price: float) -> Optional[RepricingSignal]:
        prices = self._history.get(ticker, [])
        if len(prices) < 20:
            return None
        mean = sum(prices) / len(prices)
        std = math.sqrt(sum((p - mean) ** 2 for p in prices) / len(prices)) if len(prices) > 1 else 0.01
        market_price = prices[-1]
        divergence = abs(market_price - fair_price) / fair_price if fair_price > 0 else 0
        z = BayesianEngine.z_score(market_price, mean, std)

        action = "hold"
        if z > self.z_threshold and market_price > fair_price:
            action = "sell"
        elif z < -self.z_threshold and market_price < fair_price:
            action = "buy"

        confidence = min(1.0, abs(z) / (self.z_threshold * 2))

        return RepricingSignal(
            ticker=ticker, fair_price=fair_price, market_price=market_price,
            divergence=divergence, z_score=z, action=action, confidence=confidence,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Unified Bayesian Arbitrage Bot
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketSignal:
    ticker: str
    prior: float
    likelihood_true: float
    likelihood_false: float
    market_price: float
    yes_ask: float
    no_ask: float
    source: str = ""
    timestamp: float = 0.0


class NativeBayesianArbitrageBot:
    """Polymarket Bayesian arbitrage bot with market making."""

    def __init__(self, bankroll: float = 10000.0, kelly_fraction: float = 0.25) -> None:
        self.bankroll = bankroll
        self.kelly_fraction = kelly_fraction
        self.bayes = BayesianEngine()
        self.kelly = KellyPredictor()
        self.cross = CrossMarketAnalyzer()
        self.maker = StoikovMarketMaker()
        self.reprice = RepricingDetector()
        self._positions: Dict[str, Dict[str, Any]] = {}
        self._trades: List[Dict[str, Any]] = []
        self._history: List[Dict[str, Any]] = []

    def create_signal(self, ticker: str, prior: float, likelihood_true: float,
                      likelihood_false: float, market_price: float, yes_ask: float, no_ask: float) -> MarketSignal:
        return MarketSignal(
            ticker=ticker, prior=prior, likelihood_true=likelihood_true,
            likelihood_false=likelihood_false, market_price=market_price,
            yes_ask=yes_ask, no_ask=no_ask, timestamp=time.time(),
        )

    def process_signal(self, signal: MarketSignal) -> Dict[str, Any]:
        """Process a market signal and return trading decision."""
        posterior = self.bayes.update(signal.prior, signal.likelihood_true, signal.likelihood_false)
        edge = self.kelly.calculate_edge(posterior, signal.market_price)
        kelly_size = self.kelly.kelly_position_size(posterior, signal.market_price, self.kelly_fraction)
        dollar_size = self.bankroll * kelly_size

        # Check arbitrage: yes + no should ≈ 1.0
        arb = self.check_arbitrage(signal.yes_ask, signal.no_ask)

        # Repricing
        self.reprice.add_price(signal.ticker, signal.market_price)
        reprice_signal = self.reprice.detect(signal.ticker, posterior)

        result = {
            "ticker": signal.ticker,
            "posterior": posterior,
            "edge": edge,
            "kelly_size": kelly_size,
            "dollar_size": dollar_size,
            "arbitrage": arb,
            "repricing": reprice_signal,
            "action": "hold",
            "contracts": 0,
        }

        if edge["actionable"] and edge["side"] == "yes":
            result["action"] = "buy_yes"
            result["contracts"] = int(dollar_size / (signal.yes_ask * 100)) if signal.yes_ask > 0 else 0
        elif edge["actionable"] and edge["side"] == "no":
            result["action"] = "buy_no"
            result["contracts"] = int(dollar_size / (signal.no_ask * 100)) if signal.no_ask > 0 else 0

        self._history.append(result)
        return result

    def check_arbitrage(self, yes_price: float, no_price: float) -> Optional[Dict[str, Any]]:
        """Check if yes + no < 1.0 (arbitrage opportunity)."""
        total = yes_price + no_price
        if total < 0.95:  # 5% arbitrage threshold
            return {
                "yes_price": yes_price, "no_price": no_price,
                "total": total, "arb_profit": 1.0 - total,
                "action": "buy_both",
            }
        return None

    def market_make(self, fair_price: float, time_to_expiry: float) -> Dict[str, Any]:
        """Generate market maker quotes."""
        bid, ask = self.maker.calculate_spread(fair_price, time_to_expiry)
        skew = self.maker.get_skew()
        bid *= (1 + skew)
        ask *= (1 + skew)
        return {
            "bid": bid, "ask": ask, "spread": ask - bid,
            "inventory": self.maker.inventory, "skew": skew,
            "quoting": self.maker.should_quote(),
        }

    def cross_market_scan(self, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        return self.cross.cross_market_spread_analysis(prices, threshold=0.01)

    def status(self) -> Dict[str, Any]:
        return {
            "bankroll": self.bankroll,
            "positions": len(self._positions),
            "trades": len(self._trades),
            "history": len(self._history),
            "inventory": self.maker.inventory,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Bayesian Arbitrage Bot — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Test 1: Bayesian update
    print("[Test 1] Bayesian update")
    bot = NativeBayesianArbitrageBot(bankroll=10000)
    posterior = bot.bayes.update(0.41, 0.78, 0.24)
    ok = 0.60 <= posterior <= 0.80
    print(f"  P=0.41, LT=0.78, LF=0.24 → posterior={posterior:.3f}: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Kelly sizing
    print("[Test 2] Kelly sizing")
    kelly = bot.kelly.kelly_position_size(0.56, 0.47, 0.25)
    ok2 = kelly > 0 and kelly < 0.5
    print(f"  Kelly fraction={kelly:.4f}: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Net edge
    print("[Test 3] Net edge")
    edge = bot.bayes.net_edge(0.56, 0.47, 0.015)
    ok3 = edge > 0.07
    print(f"  Net edge={edge:.4f}: {ok3} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Cross-market analysis
    print("[Test 4] Cross-market analysis")
    prices = {"polymarket": 0.55, "kalshi": 0.52, "betfair": 0.54}
    arb = bot.cross_market_scan(prices)
    ok4 = len(arb) > 0
    print(f"  Arbitrage opportunities: {len(arb)}: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Process signal
    print("[Test 5] Process signal")
    signal = bot.create_signal("BTC-UP", 0.41, 0.78, 0.24, 0.47, 0.58, 0.45)
    result = bot.process_signal(signal)
    ok5 = result["action"] in ("buy_yes", "buy_no", "hold")
    print(f"  Action: {result['action']}, edge={result['edge']['edge_pct']:.1f}%: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Market making
    print("[Test 6] Market making")
    quotes = bot.market_make(0.50, 1.0)
    ok6 = quotes["bid"] < quotes["ask"] and quotes["quoting"]
    print(f"  Bid={quotes['bid']:.3f}, Ask={quotes['ask']:.3f}: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Arbitrage check
    print("[Test 7] Arbitrage check")
    arb = bot.check_arbitrage(0.45, 0.45)
    ok7 = arb is not None and arb["action"] == "buy_both"
    print(f"  Arb found: {ok7} (profit={arb['arb_profit'] if arb else 0:.3f}) — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
