"""LLM Stock Analyzer — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

@dataclass
class StockPrice:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class StockAnalyzer:
    def __init__(self) -> None:
        self._prices: List[StockPrice] = []

    def add_price(self, price: StockPrice) -> None:
        self._prices.append(price)

    def moving_average(self, period: int = 20) -> List[float]:
        if len(self._prices) < period:
            return []
        mas = []
        for i in range(period, len(self._prices) + 1):
            window = self._prices[i - period:i]
            ma = sum(p.close for p in window) / period
            mas.append(ma)
        return mas

    def rsi(self, period: int = 14) -> Optional[float]:
        if len(self._prices) < period + 1:
            return None
        gains = []
        losses = []
        for i in range(1, len(self._prices)):
            change = self._prices[i].close - self._prices[i - 1].close
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-change)
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def volatility(self, period: int = 20) -> float:
        if len(self._prices) < period:
            return 0.0
        returns = []
        for i in range(1, len(self._prices)):
            ret = (self._prices[i].close - self._prices[i - 1].close) / self._prices[i - 1].close
            returns.append(ret)
        recent = returns[-period:]
        mean = sum(recent) / len(recent)
        variance = sum((r - mean) ** 2 for r in recent) / len(recent)
        return variance ** 0.5

    def support_resistance(self, window: int = 10) -> tuple:
        if len(self._prices) < window:
            return (0.0, 0.0)
        recent = self._prices[-window:]
        lows = [p.low for p in recent]
        highs = [p.high for p in recent]
        return (min(lows), max(highs))

    def get_stats(self) -> Dict[str, Any]:
        if not self._prices:
            return {}
        closes = [p.close for p in self._prices]
        return {"prices": len(self._prices), "min": min(closes), "max": max(closes), "avg": sum(closes) / len(closes), "latest": closes[-1]}

def run() -> None:
    print("Stock Analyzer test")
    e = StockAnalyzer()
    for i in range(30):
        e.add_price(StockPrice("2024-01-" + str(i + 1), 100 + i, 105 + i, 98 + i, 102 + i, 1000000 + i * 1000))
    print("  MA(5): " + str(e.moving_average(5)[:3]))
    print("  RSI: " + str(e.rsi(14)))
    print("  Volatility: " + str(e.volatility(10)))
    print("  Support/Resistance: " + str(e.support_resistance(10)))
    print("  Stats: " + str(e.get_stats()))
    print("Stock Analyzer test complete.")

if __name__ == "__main__":
    run()
