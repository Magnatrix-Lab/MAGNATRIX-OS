"""Anomaly Detector TS - Time series anomaly detection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
import math

class AnomalyMethod(Enum):
    ZSCORE = auto()
    IQR = auto()
    MAD = auto()

@dataclass
class AnomalyDetectorTS:
    method: AnomalyMethod = AnomalyMethod.ZSCORE
    threshold: float = 3.0
    anomalies: List[int] = field(default_factory=list)

    def detect(self, data: List[float]) -> List[int]:
        self.anomalies = []
        if len(data) < 2:
            return self.anomalies
        if self.method == AnomalyMethod.ZSCORE:
            mean = sum(data) / len(data)
            std = math.sqrt(sum((x - mean)**2 for x in data) / len(data))
            for i, x in enumerate(data):
                if std > 0 and abs((x - mean) / std) > self.threshold:
                    self.anomalies.append(i)
        elif self.method == AnomalyMethod.IQR:
            sorted_d = sorted(data)
            q1 = sorted_d[len(sorted_d)//4]
            q3 = sorted_d[3*len(sorted_d)//4]
            iqr = q3 - q1
            lower, upper = q1 - 1.5*iqr, q3 + 1.5*iqr
            for i, x in enumerate(data):
                if x < lower or x > upper:
                    self.anomalies.append(i)
        elif self.method == AnomalyMethod.MAD:
            median = sorted(data)[len(data)//2]
            mad = sum(abs(x - median) for x in data) / len(data)
            for i, x in enumerate(data):
                if mad > 0 and abs(x - median) / mad > self.threshold:
                    self.anomalies.append(i)
        return self.anomalies

    def stats(self, data: List[float]) -> dict:
        return {"method": self.method.name, "threshold": self.threshold, "anomalies": len(self.anomalies), "anomaly_rate": round(len(self.anomalies)/len(data), 4) if data else 0}

def run():
    data = [10, 12, 11, 13, 100, 12, 11, 9, 10, 11]
    for method in [AnomalyMethod.ZSCORE, AnomalyMethod.IQR, AnomalyMethod.MAD]:
        ad = AnomalyDetectorTS(method, 2.0)
        anom = ad.detect(data)
        print(f"{method.name}: anomalies at {anom}, stats={ad.stats(data)}")

if __name__ == "__main__":
    run()
