"""LLM Anomaly Finder — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class AnomalyType(Enum):
    POINT = auto()
    CONTEXTUAL = auto()
    COLLECTIVE = auto()

class AnomalyFinder:
    def __init__(self) -> None:
        self._threshold: float = 2.0

    def set_threshold(self, threshold: float) -> None:
        self._threshold = threshold

    def zscore_detect(self, values: List[float]) -> List[int]:
        if len(values) < 2:
            return []
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 1.0
        anomalies = []
        for i, v in enumerate(values):
            zscore = abs(v - mean) / std if std > 0 else 0.0
            if zscore > self._threshold:
                anomalies.append(i)
        return anomalies

    def iqr_detect(self, values: List[float]) -> List[int]:
        if len(values) < 4:
            return []
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[3 * n // 4]
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        anomalies = []
        for i, v in enumerate(values):
            if v < lower or v > upper:
                anomalies.append(i)
        return anomalies

    def moving_average_detect(self, values: List[float], window: int = 3) -> List[int]:
        if len(values) < window + 1:
            return []
        anomalies = []
        for i in range(window, len(values)):
            recent = values[i - window:i]
            avg = sum(recent) / len(recent)
            std = math.sqrt(sum((v - avg) ** 2 for v in recent) / len(recent)) if len(recent) > 0 else 0.0
            if std > 0 and abs(values[i] - avg) > self._threshold * std:
                anomalies.append(i)
        return anomalies

    def get_stats(self, values: List[float], anomalies: List[int]) -> Dict[str, Any]:
        return {"total": len(values), "anomalies": len(anomalies), "rate": len(anomalies) / len(values) if values else 0.0, "anomaly_values": [values[i] for i in anomalies]}

def run() -> None:
    print("Anomaly Finder test")
    e = AnomalyFinder()
    e.set_threshold(1.5)
    values = [1, 2, 2, 3, 2, 100, 2, 3, 2, 1]
    z_anomalies = e.zscore_detect(values)
    iqr_anomalies = e.iqr_detect(values)
    ma_anomalies = e.moving_average_detect(values, 3)
    print("  Values: " + str(values))
    print("  Z-score anomalies: " + str(z_anomalies))
    print("  IQR anomalies: " + str(iqr_anomalies))
    print("  MA anomalies: " + str(ma_anomalies))
    print("  Stats: " + str(e.get_stats(values, z_anomalies)))
    print("Anomaly Finder test complete.")

if __name__ == "__main__":
    run()
