"""Fault Detector — anomaly, root cause, severity, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class FaultDetector:
    thresholds: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    """metric -> (warning, critical)"""
    readings: Dict[str, List[float]] = field(default_factory=dict)

    def add_metric(self, name: str, warning: float, critical: float):
        self.thresholds[name] = (warning, critical)

    def record(self, name: str, value: float):
        self.readings.setdefault(name, []).append(value)

    def check(self, name: str) -> str:
        vals = self.readings.get(name, [])
        if not vals:
            return "unknown"
        latest = vals[-1]
        w, c = self.thresholds.get(name, (0, 0))
        if latest >= c:
            return "critical"
        elif latest >= w:
            return "warning"
        return "normal"

    def anomalies(self, name: str, std_factor: float = 2.0) -> List[int]:
        vals = self.readings.get(name, [])
        if len(vals) < 3:
            return []
        m = sum(vals) / len(vals)
        s = (sum((v - m)**2 for v in vals) / len(vals)) ** 0.5
        return [i for i, v in enumerate(vals) if abs(v - m) > std_factor * s]

    def root_cause_candidates(self, faults: List[str]) -> List[str]:
        """Return metrics that went critical first."""
        first_faults = []
        for f in faults:
            vals = self.readings.get(f, [])
            w, c = self.thresholds.get(f, (0, 0))
            for i, v in enumerate(vals):
                if v >= c:
                    first_faults.append((f, i))
                    break
        first_faults.sort(key=lambda x: x[1])
        return [f for f, _ in first_faults]

    def stats(self) -> Dict:
        statuses = {name: self.check(name) for name in self.thresholds}
        critical = sum(1 for s in statuses.values() if s == "critical")
        warning = sum(1 for s in statuses.values() if s == "warning")
        return {"metrics": len(self.thresholds), "critical": critical, "warning": warning}

def run():
    fd = FaultDetector()
    fd.add_metric("cpu", 70, 90)
    fd.add_metric("memory", 80, 95)
    fd.record("cpu", 45)
    fd.record("cpu", 75)
    fd.record("cpu", 92)
    fd.record("memory", 60)
    fd.record("memory", 85)
    print(fd.stats())
    print("CPU status:", fd.check("cpu"))
    print("Anomalies:", fd.anomalies("cpu"))

if __name__ == "__main__":
    run()
