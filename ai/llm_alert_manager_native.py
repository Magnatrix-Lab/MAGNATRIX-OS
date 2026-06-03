"""LLM Alert Manager — Native Python (stdlib only)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class AlertSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()
    EMERGENCY = auto()

class AlertStatus(Enum):
    ACTIVE = auto()
    ACKNOWLEDGED = auto()
    RESOLVED = auto()

@dataclass
class Alert:
    id: str
    severity: AlertSeverity
    message: str
    source: str
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: float = 0.0
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class AlertManager:
    def __init__(self) -> None:
        self._alerts: Dict[str, Alert] = {}
        self._handlers: List[Callable[[Alert], None]] = []

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        self._handlers.append(handler)

    def trigger(self, alert: Alert) -> None:
        alert.created_at = time.time()
        self._alerts[alert.id] = alert
        for handler in self._handlers:
            handler(alert)

    def acknowledge(self, alert_id: str) -> bool:
        alert = self._alerts.get(alert_id)
        if alert and alert.status == AlertStatus.ACTIVE:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = time.time()
            return True
        return False

    def resolve(self, alert_id: str) -> bool:
        alert = self._alerts.get(alert_id)
        if alert and alert.status in (AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED):
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()
            return True
        return False

    def get_active(self) -> List[Alert]:
        return [a for a in self._alerts.values() if a.status == AlertStatus.ACTIVE]

    def get_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        return [a for a in self._alerts.values() if a.severity == severity]

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for a in self._alerts.values():
            counts[a.status.name] = counts.get(a.status.name, 0) + 1
        return {"total": len(self._alerts), "by_status": counts, "active": len(self.get_active())}

def run() -> None:
    print("Alert Manager test")
    e = AlertManager()
    e.add_handler(lambda a: print("  ALERT: " + a.severity.name + " - " + a.message))
    e.trigger(Alert("a1", AlertSeverity.WARNING, "High CPU usage", "monitor"))
    e.trigger(Alert("a2", AlertSeverity.CRITICAL, "Disk full", "monitor"))
    e.acknowledge("a1")
    e.resolve("a1")
    print("  Active: " + str(len(e.get_active())))
    print("  Critical: " + str(len(e.get_by_severity(AlertSeverity.CRITICAL))))
    print("  Stats: " + str(e.get_stats()))
    print("Alert Manager test complete.")

if __name__ == "__main__":
    run()
