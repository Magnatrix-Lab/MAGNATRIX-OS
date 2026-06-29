"""
stock_signal_generator_native.py
MAGNATRIX-OS — Stock Signal Generator

Inspired by daily_stock_analysis signal attribution:
Generate trading signals from technical indicators and price action. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class StockSignal:
    symbol: str
    signal_type: str
    direction: str
    strength: float
    indicator: str
    trigger_price: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class StockSignalGenerator:
    """Generate trading signals from technical analysis."""

    SIGNAL_TYPES = ["crossover", "breakout", "oversold", "overbought", "divergence", "volume_spike"]

    def __init__(self, signals_dir: str = "./stock_signals"):
        self.signals_dir = Path(signals_dir)
        self.signals_dir.mkdir(exist_ok=True)
        self.signals: List[StockSignal] = []
        self._load()

    def _load(self) -> None:
        file = self.signals_dir / "signals.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.signals = [StockSignal(**s) for s in data]
            except Exception:
                pass

    def _save(self) -> None:
        file = self.signals_dir / "signals.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in self.signals], f, indent=2)

    def _calc_sma(self, prices: List[float], period: int) -> float:
        if len(prices) < period:
            return sum(prices) / len(prices) if prices else 0.0
        return sum(prices[-period:]) / period

    def _calc_rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        gains, losses = [], []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1 + rs))

    def _calc_macd(self, prices: List[float]) -> tuple:
        ema12 = self._calc_sma(prices, 12)
        ema26 = self._calc_sma(prices, 26)
        macd = ema12 - ema26
        signal = self._calc_sma(prices[-9:], 9) if len(prices) >= 9 else 0
        return macd, signal

    def generate_signals(self, symbol: str, price_data: List[Dict[str, Any]]) -> List[StockSignal]:
        if not price_data:
            return []
        closes = [d["close"] for d in price_data]
        latest = closes[-1]
        signals = []

        # Moving Average Crossover
        sma5 = self._calc_sma(closes, 5)
        sma20 = self._calc_sma(closes, 20)
        if len(closes) >= 20:
            prev_sma5 = self._calc_sma(closes[:-1], 5)
            prev_sma20 = self._calc_sma(closes[:-1], 20)
            if prev_sma5 <= prev_sma20 and sma5 > sma20:
                signals.append(StockSignal(symbol, "crossover", "BUY", 0.7, "MA5/MA20", latest))
            elif prev_sma5 >= prev_sma20 and sma5 < sma20:
                signals.append(StockSignal(symbol, "crossover", "SELL", 0.7, "MA5/MA20", latest))

        # RSI signals
        rsi = self._calc_rsi(closes)
        if rsi < 30:
            signals.append(StockSignal(symbol, "oversold", "BUY", 0.8, "RSI", latest))
        elif rsi > 70:
            signals.append(StockSignal(symbol, "overbought", "SELL", 0.8, "RSI", latest))

        # Volume spike
        if len(price_data) >= 2 and "volume" in price_data[-1] and "volume" in price_data[-2]:
            vol_ratio = price_data[-1]["volume"] / max(1, price_data[-2]["volume"])
            if vol_ratio > 2.0:
                direction = "BUY" if closes[-1] > closes[-2] else "SELL"
                signals.append(StockSignal(symbol, "volume_spike", direction, 0.6, "Volume", latest))

        self.signals.extend(signals)
        self._save()
        return signals

    def get_active_signals(self, symbol: Optional[str] = None) -> List[StockSignal]:
        if symbol:
            return [s for s in self.signals if s.symbol == symbol]
        return self.signals

    def get_stats(self) -> Dict[str, Any]:
        buy_count = sum(1 for s in self.signals if s.direction == "BUY")
        sell_count = sum(1 for s in self.signals if s.direction == "SELL")
        return {"total_signals": len(self.signals), "buy": buy_count, "sell": sell_count}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["StockSignalGenerator", "StockSignal"]