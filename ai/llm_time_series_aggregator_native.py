"""Time Series Aggregator - Rolling aggregations for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

class AggType(Enum):
    MEAN = auto(); SUM = auto(); MIN = auto(); MAX = auto(); STD = auto()

@dataclass
class TimeSeriesAggregator:
    window_size: int = 5
    agg_type: AggType = AggType.MEAN

    def aggregate(self, values: List[float]) -> List[float]:
        result = []
        for i in range(len(values)):
            window = values[max(0, i - self.window_size + 1):i + 1]
            if self.agg_type == AggType.MEAN: result.append(sum(window) / len(window))
            elif self.agg_type == AggType.SUM: result.append(sum(window))
            elif self.agg_type == AggType.MIN: result.append(min(window))
            elif self.agg_type == AggType.MAX: result.append(max(window))
            elif self.agg_type == AggType.STD:
                m = sum(window) / len(window)
                result.append(math.sqrt(sum((v - m)**2 for v in window) / len(window)))
        return result

    def stats(self, values: List[float]) -> dict:
        agg = self.aggregate(values)
        return {"agg_type": self.agg_type.name, "window": self.window_size, "latest": round(agg[-1], 4) if agg else 0}

def run():
    tsa = TimeSeriesAggregator(3, AggType.MEAN)
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    print("Aggregated:", [round(v, 2) for v in tsa.aggregate(values)])
    print("Stats:", tsa.stats(values))

if __name__ == "__main__": run()
