"""Exponential Smoother - Holt-Winters smoothing for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto

class SmoothType(Enum):
    SIMPLE = auto(); HOLT = auto(); WINTERS = auto()

@dataclass
class ExponentialSmoother:
    smooth_type: SmoothType = SmoothType.SIMPLE
    alpha: float = 0.3
    beta: float = 0.1
    gamma: float = 0.1
    season_length: int = 4

    def smooth(self, data: List[float]) -> List[float]:
        if not data: return []
        if self.smooth_type == SmoothType.SIMPLE:
            s = data[0]
            result = [s]
            for x in data[1:]:
                s = self.alpha * x + (1 - self.alpha) * s
                result.append(s)
            return result
        elif self.smooth_type == SmoothType.HOLT:
            s, b = data[0], (data[1] - data[0]) if len(data) > 1 else 0
            result = [s]
            for x in data[1:]:
                s_new = self.alpha * x + (1 - self.alpha) * (s + b)
                b = self.beta * (s_new - s) + (1 - self.beta) * b
                s = s_new
                result.append(s + b)
            return result
        return data

    def stats(self, data: List[float]) -> dict:
        smoothed = self.smooth(data)
        return {"type": self.smooth_type.name, "alpha": self.alpha, "last_smoothed": round(smoothed[-1], 4) if smoothed else 0}

def run():
    es = ExponentialSmoother(SmoothType.HOLT, 0.3, 0.1)
    data = [10, 12, 15, 13, 16, 18, 17, 19, 21, 20]
    smoothed = es.smooth(data)
    print("Smoothed:", [round(v, 2) for v in smoothed])
    print("Stats:", es.stats(data))

if __name__ == "__main__": run()
