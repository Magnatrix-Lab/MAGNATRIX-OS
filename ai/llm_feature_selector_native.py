"""Feature Selector - Auto feature selection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
import random

class SelectionMethod(Enum):
    VARIANCE = auto(); CORRELATION = auto(); MUTUAL_INFO = auto()

@dataclass
class FeatureSelector:
    method: SelectionMethod = SelectionMethod.VARIANCE
    k: int = 3

    def variance(self, data: List[List[float]]) -> List[int]:
        variances = []
        for j in range(len(data[0])):
            col = [row[j] for row in data]
            m = sum(col)/len(col)
            variances.append(sum((x-m)**2 for x in col)/len(col))
        return sorted(range(len(variances)), key=lambda i: variances[i], reverse=True)[:self.k]

    def correlation(self, data: List[List[float]], target: List[float]) -> List[int]:
        corrs = []
        for j in range(len(data[0])):
            col = [row[j] for row in data]
            mc = sum(col)/len(col); mt = sum(target)/len(target)
            num = sum((col[i]-mc)*(target[i]-mt) for i in range(len(col)))
            den = math.sqrt(sum((c-mc)**2 for c in col)) * math.sqrt(sum((t-mt)**2 for t in target))
            corrs.append(abs(num/den) if den > 0 else 0)
        return sorted(range(len(corrs)), key=lambda i: corrs[i], reverse=True)[:self.k]

    def select(self, data: List[List[float]], target: List[float] = None) -> List[int]:
        if self.method == SelectionMethod.VARIANCE: return self.variance(data)
        if self.method == SelectionMethod.CORRELATION and target: return self.correlation(data, target)
        return list(range(min(self.k, len(data[0]))))

    def stats(self, data: List[List[float]]) -> dict:
        return {"method": self.method.name, "selected": self.select(data)}

def run():
    fs = FeatureSelector(SelectionMethod.VARIANCE, 2)
    data = [[1,2,3],[1,2,3],[1,20,3]]
    print("Selected:", fs.select(data))
    print("Stats:", fs.stats(data))

if __name__ == "__main__": run()
