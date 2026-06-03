"""Time Series Decomposer - Trend/seasonality/residual for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
import math

class DecompositionType(Enum):
    ADDITIVE = auto()
    MULTIPLICATIVE = auto()

@dataclass
class TimeSeriesDecomposer:
    period: int = 4
    decomp_type: DecompositionType = DecompositionType.ADDITIVE
    trend: List[float] = field(default_factory=list)
    seasonal: List[float] = field(default_factory=list)
    residual: List[float] = field(default_factory=list)

    def moving_average(self, data: List[float], window: int) -> List[float]:
        half = window // 2
        result = []
        for i in range(len(data)):
            start = max(0, i - half)
            end = min(len(data), i + half + 1)
            result.append(sum(data[start:end]) / (end - start))
        return result

    def decompose(self, data: List[float]) -> dict:
        self.trend = self.moving_average(data, self.period)
        detrended = [data[i] - self.trend[i] for i in range(len(data))]
        seasonal_pattern = []
        for i in range(self.period):
            values = [detrended[j] for j in range(i, len(detrended), self.period)]
            seasonal_pattern.append(sum(values) / len(values))
        mean_season = sum(seasonal_pattern) / len(seasonal_pattern)
        self.seasonal = [seasonal_pattern[i % self.period] - mean_season for i in range(len(data))]
        self.residual = [data[i] - self.trend[i] - self.seasonal[i] for i in range(len(data))]
        return {"trend": self.trend, "seasonal": self.seasonal, "residual": self.residual}

    def stats(self) -> dict:
        return {"period": self.period, "type": self.decomp_type.name, "length": len(self.trend)}

def run():
    data = [10, 12, 15, 13, 11, 13, 16, 14, 12, 14, 17, 15]
    decomp = TimeSeriesDecomposer(4)
    result = decomp.decompose(data)
    print("Trend:", [round(v, 2) for v in result["trend"]])
    print("Residual:", [round(v, 2) for v in result["residual"]])
    print("Stats:", decomp.stats())

if __name__ == "__main__":
    run()
