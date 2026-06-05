"""Trend Analyzer — time series trends, momentum, breakout, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class TrendAnalyzer:
    data: List[float] = field(default_factory=list)

    def moving_average(self, window: int) -> List[float]:
        if window > len(self.data):
            return []
        return [sum(self.data[i:i+window]) / window for i in range(len(self.data) - window + 1)]

    def linear_trend(self) -> Tuple[float, float]:
        n = len(self.data)
        if n < 2:
            return 0.0, 0.0
        x = list(range(n))
        mx, my = sum(x)/n, sum(self.data)/n
        sx = sum((xi - mx)**2 for xi in x)
        sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, self.data))
        slope = sxy / sx if sx > 0 else 0.0
        intercept = my - slope * mx
        return slope, intercept

    def momentum(self, period: int = 10) -> float:
        if len(self.data) < period + 1:
            return 0.0
        return self.data[-1] - self.data[-period-1]

    def breakout_detection(self, window: int = 20, threshold: float = 2.0) -> List[int]:
        if len(self.data) < window:
            return []
        breaks = []
        for i in range(window, len(self.data)):
            recent = self.data[i-window:i]
            ma = sum(recent) / len(recent)
            std = math.sqrt(sum((x - ma)**2 for x in recent) / len(recent))
            if std > 0 and abs(self.data[i] - ma) > threshold * std:
                breaks.append(i)
        return breaks

    def stats(self) -> Dict:
        slope, _ = self.linear_trend()
        return {"slope": round(slope, 4), "momentum": self.momentum(), "breakouts": len(self.breakout_detection())}

def run():
    ta = TrendAnalyzer([1,2,3,4,5,6,7,8,9,10,20,21,22])
    print("MA:", ta.moving_average(3))
    print("Trend:", ta.linear_trend())
    print("Breakouts:", ta.breakout_detection())
    print(ta.stats())

if __name__ == "__main__":
    run()
