"""
technical_indicator_native.py
MAGNATRIX-OS — Technical Indicator Calculator

Calculate technical indicators for stock analysis: SMA, EMA, RSI, MACD, Bollinger Bands, ATR. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class IndicatorResult:
    symbol: str
    indicator: str
    period: int
    values: List[float] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)


class TechnicalIndicator:
    """Calculate technical indicators for stock analysis."""

    def __init__(self, cache_dir: str = "./indicator_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache: Dict[str, Dict[str, Any]] = {}

    def _key(self, symbol: str, indicator: str, period: int) -> str:
        return f"{symbol}_{indicator}_{period}"

    def sma(self, prices: List[float], period: int) -> List[float]:
        if len(prices) < period:
            return []
        return [sum(prices[i:i+period]) / period for i in range(len(prices) - period + 1)]

    def ema(self, prices: List[float], period: int) -> List[float]:
        if len(prices) < period:
            return []
        multiplier = 2 / (period + 1)
        ema_vals = [sum(prices[:period]) / period]
        for i in range(period, len(prices)):
            ema_vals.append((prices[i] - ema_vals[-1]) * multiplier + ema_vals[-1])
        return ema_vals

    def rsi(self, prices: List[float], period: int = 14) -> List[float]:
        if len(prices) < period + 1:
            return []
        rsi_vals = []
        gains, losses = [], []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            gains.append(max(diff, 0))
            losses.append(abs(min(diff, 0)))
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi_vals.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_vals.append(100.0 - (100.0 / (1 + rs)))
        return rsi_vals

    def macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
        ema_fast = self.ema(prices, fast)
        ema_slow = self.ema(prices, slow)
        if not ema_fast or not ema_slow:
            return {"macd": [], "signal": [], "histogram": []}
        # Align
        offset = len(ema_fast) - len(ema_slow)
        aligned_fast = ema_fast[offset:] if offset > 0 else ema_fast
        aligned_slow = ema_slow
        macd_line = [f - s for f, s in zip(aligned_fast, aligned_slow)]
        signal_line = self.ema(macd_line, signal)
        hist = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
        return {"macd": macd_line, "signal": signal_line, "histogram": hist}

    def bollinger(self, prices: List[float], period: int = 20, std_dev: int = 2) -> Dict[str, List[float]]:
        if len(prices) < period:
            return {"middle": [], "upper": [], "lower": []}
        middle = []
        upper, lower = [], []
        for i in range(len(prices) - period + 1):
            window = prices[i:i+period]
            avg = sum(window) / period
            variance = sum((p - avg) ** 2 for p in window) / period
            std = variance ** 0.5
            middle.append(avg)
            upper.append(avg + std_dev * std)
            lower.append(avg - std_dev * std)
        return {"middle": middle, "upper": upper, "lower": lower}

    def atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
        if len(highs) < 2 or len(lows) < 2 or len(closes) < 2:
            return []
        trs = []
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            trs.append(max(tr1, tr2, tr3))
        if len(trs) < period:
            return []
        atr_vals = [sum(trs[:period]) / period]
        for i in range(period, len(trs)):
            atr_vals.append((atr_vals[-1] * (period - 1) + trs[i]) / period)
        return atr_vals

    def calculate(self, symbol: str, prices: List[float], indicator: str, period: int = 14) -> IndicatorResult:
        if indicator == "sma":
            vals = self.sma(prices, period)
        elif indicator == "ema":
            vals = self.ema(prices, period)
        elif indicator == "rsi":
            vals = self.rsi(prices, period)
        elif indicator == "macd":
            vals = self.macd(prices)["macd"]
        elif indicator == "bollinger_upper":
            vals = self.bollinger(prices, period)["upper"]
        elif indicator == "bollinger_lower":
            vals = self.bollinger(prices, period)["lower"]
        else:
            vals = []
        signals = []
        if indicator == "rsi" and vals:
            signals = ["oversold" if v < 30 else "overbought" if v > 70 else "neutral" for v in vals[-5:]]
        return IndicatorResult(symbol=symbol, indicator=indicator, period=period, values=vals, signals=signals)

    def get_stats(self) -> Dict[str, Any]:
        return {"indicators_supported": ["sma", "ema", "rsi", "macd", "bollinger", "atr"]}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TechnicalIndicator", "IndicatorResult"]