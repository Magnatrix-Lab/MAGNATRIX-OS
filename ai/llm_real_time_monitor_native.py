"""Real Time Monitor - Metric monitoring for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import time

class AlertLevel(Enum):
    INFO = auto(); WARNING = auto(); CRITICAL = auto()

@dataclass
class RealTimeMonitor:
    metrics: Dict[str, List[Dict]] = field(default_factory=dict)
    thresholds: Dict[str, Tuple[float, AlertLevel]] = field(default_factory=dict)
    alerts: List[Dict] = field(default_factory=list)

    def set_threshold(self, metric: str, threshold: float, level: AlertLevel = AlertLevel.WARNING) -> None:
        self.thresholds[metric] = (threshold, level)

    def record(self, metric: str, value: float) -> Optional[AlertLevel]:
        if metric not in self.metrics: self.metrics[metric] = []
        self.metrics[metric].append({"value": value, "time": time.time()})
        if metric in self.thresholds:
            thresh, level = self.thresholds[metric]
            if value > thresh:
                self.alerts.append({"metric": metric, "value": value, "threshold": thresh, "level": level.name, "time": time.time()})
                return level
        return None

    def stats(self) -> dict:
        return {"metrics": len(self.metrics), "alerts": len(self.alerts), "thresholds": len(self.thresholds)}

def run():
    rtm = RealTimeMonitor()
    rtm.set_threshold("cpu", 80.0, AlertLevel.CRITICAL)
    for v in [30, 50, 85, 90]:
        alert = rtm.record("cpu", v)
        print(f"CPU {v}: {alert.name if alert else 'OK'}")
    print("Stats:", rtm.stats())

if __name__ == "__main__": run()
