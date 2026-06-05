"""IDS Engine — intrusion detection, anomaly, signature, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
import time
import re

class AlertSeverity(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

@dataclass
class IDSSignature:
    sig_id: str
    pattern: str
    protocol: str
    severity: AlertSeverity
    description: str

@dataclass
class IDSAlert:
    alert_id: str
    sig_id: str
    timestamp: float
    source: str
    severity: AlertSeverity
    description: str

class IDSEngine:
    def __init__(self, anomaly_threshold: float = 2.0):
        self.anomaly_threshold = anomaly_threshold
        self.signatures: List[IDSSignature] = []
        self.alerts: List[IDSAlert] = []
        self.baseline: Dict[str, List[float]] = {}
        self.event_count: Dict[str, int] = {}

    def add_signature(self, sig: IDSSignature):
        self.signatures.append(sig)

    def add_baseline(self, metric: str, values: List[float]):
        self.baseline[metric] = values

    def detect_signature(self, event: Dict) -> List[IDSAlert]:
        alerts = []
        for sig in self.signatures:
            if re.search(sig.pattern, str(event.get("payload", ""))):
                alert = IDSAlert(str(len(self.alerts)), sig.sig_id, time.time(), event.get("source", "unknown"), sig.severity, sig.description)
                self.alerts.append(alert)
                alerts.append(alert)
        return alerts

    def detect_anomaly(self, metric: str, value: float) -> Optional[IDSAlert]:
        baseline = self.baseline.get(metric, [])
        if not baseline:
            return None
        mean = sum(baseline) / len(baseline)
        std = (sum((x - mean) ** 2 for x in baseline) / len(baseline)) ** 0.5
        if std > 0 and abs(value - mean) / std > self.anomaly_threshold:
            alert = IDSAlert(str(len(self.alerts)), "ANOMALY", time.time(), metric, AlertSeverity.HIGH, f"Anomaly: {value} vs baseline {mean}")
            self.alerts.append(alert)
            return alert
        return None

    def stats(self) -> Dict:
        sev_counts = {}
        for a in self.alerts:
            sev_counts[a.severity.name] = sev_counts.get(a.severity.name, 0) + 1
        return {"signatures": len(self.signatures), "alerts": len(self.alerts), "by_severity": sev_counts}

def run():
    ids = IDSEngine(2.0)
    ids.add_signature(IDSSignature("s1", r"password=.*", "HTTP", AlertSeverity.HIGH, "Password in cleartext"))
    ids.add_baseline("cpu", [10, 12, 11, 13, 10, 12, 11])
    print(ids.detect_signature({"payload": "username=admin password=secret123", "source": "10.0.0.1"}))
    print(ids.detect_anomaly("cpu", 50))
    print(ids.stats())

if __name__ == "__main__":
    run()
