"""Outlier Detection — IQR, Z-score, isolation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import random

class OutlierMethod(Enum):
    IQR = auto()
    ZSCORE = auto()
    ISOLATION = auto()

@dataclass
class OutlierResult:
    value: float
    is_outlier: bool
    score: float

class OutlierDetector:
    def __init__(self, method: OutlierMethod = OutlierMethod.IQR, threshold: float = 1.5):
        self.method = method
        self.threshold = threshold
        self.data: List[float] = []
        self.results: List[OutlierResult] = []

    def fit(self, data: List[float]):
        self.data = sorted(data)
        self.results = []
        if self.method == OutlierMethod.IQR:
            self._iqr_detect()
        elif self.method == OutlierMethod.ZSCORE:
            self._zscore_detect()
        elif self.method == OutlierMethod.ISOLATION:
            self._isolation_detect()

    def _iqr_detect(self):
        n = len(self.data)
        q1 = self.data[n // 4] if n >= 4 else self.data[0]
        q3 = self.data[(3 * n) // 4] if n >= 4 else self.data[-1]
        iqr = q3 - q1
        lower = q1 - self.threshold * iqr
        upper = q3 + self.threshold * iqr
        for v in self.data:
            is_out = v < lower or v > upper
            score = max(lower - v, v - upper, 0) / (iqr + 1e-6)
            self.results.append(OutlierResult(v, is_out, score))

    def _zscore_detect(self):
        mean = sum(self.data) / len(self.data)
        std = math.sqrt(sum((x - mean) ** 2 for x in self.data) / len(self.data)) + 1e-6
        for v in self.data:
            z = abs(v - mean) / std
            self.results.append(OutlierResult(v, z > self.threshold, z))

    def _isolation_detect(self):
        for v in self.data:
            score = self._isolation_score(v)
            self.results.append(OutlierResult(v, score < self.threshold, score))

    def _isolation_score(self, value: float) -> float:
        # Simplified isolation score based on rank
        sorted_data = sorted(self.data)
        rank = sorted_data.index(value) if value in sorted_data else 0
        return 1.0 - (rank / len(self.data)) if self.data else 0

    def get_outliers(self) -> List[OutlierResult]:
        return [r for r in self.results if r.is_outlier]

    def stats(self) -> Dict:
        return {"method": self.method.name, "total": len(self.data), "outliers": len(self.get_outliers()), "threshold": self.threshold}

def run():
    data = [10, 12, 11, 13, 12, 100, 11, 12, 14, 11, 15, 12, 200]
    detector = OutlierDetector(OutlierMethod.IQR, threshold=1.5)
    detector.fit(data)
    print("Outliers:", [(r.value, r.score) for r in detector.get_outliers()])
    print(detector.stats())

if __name__ == "__main__":
    run()
