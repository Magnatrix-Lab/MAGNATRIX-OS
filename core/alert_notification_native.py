#!/usr/bin/env python3
"""
Alert & Notification System for MAGNATRIX-OS
Event-driven alerts, webhook dispatcher, severity escalation,
channel routing (console, webhook, file), and deduplication.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class AlertSeverity(enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel(enum.Enum):
    CONSOLE = "console"
    WEBHOOK = "webhook"
    FILE = "file"
    CALLBACK = "callback"


@dataclasses.dataclass
class Alert:
    """A single alert event."""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    source: str
    timestamp: float
    channels: List[AlertChannel] = dataclasses.field(default_factory=list)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    escalated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp,
            "channels": [c.value for c in self.channels],
            "metadata": self.metadata,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "escalated": self.escalated,
        }


class AlertNotificationManager:
    """Central alert dispatcher with routing, deduplication, and escalation."""

    def __init__(self, log_dir: str = "/tmp/magnatrix_alerts") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._alerts: Dict[str, Alert] = {}
        self._handlers: Dict[AlertChannel, Callable[[Alert], None]] = {}
        self._escalation_rules: List[Tuple[AlertSeverity, float, AlertSeverity]] = []
        self._dedup_window: float = 300.0  # 5 minutes
        self._recent: Dict[str, float] = {}  # hash -> timestamp
        self._register_defaults()

    # ------------------------------------------------------------------
    # Default handlers
    # ------------------------------------------------------------------

    def _register_defaults(self) -> None:
        self._handlers[AlertChannel.CONSOLE] = self._console_handler
        self._handlers[AlertChannel.FILE] = self._file_handler

    def _console_handler(self, alert: Alert) -> None:
        prefix = f"[{alert.severity.value.upper()}] {alert.title}"
        print(f"{prefix}: {alert.message} (source={alert.source})")

    def _file_handler(self, alert: Alert) -> None:
        path = self.log_dir / f"alerts_{time.strftime('%Y%m%d')}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(alert.to_dict(), ensure_ascii=False) + "\n")

    def _webhook_handler(self, alert: Alert) -> None:
        url = alert.metadata.get("webhook_url")
        if not url:
            return
        try:
            payload = json.dumps(alert.to_dict()).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(self, channel: AlertChannel, handler: Callable[[Alert], None]) -> None:
        self._handlers[channel] = handler

    def add_escalation_rule(self, from_severity: AlertSeverity, after_seconds: float, to_severity: AlertSeverity) -> None:
        self._escalation_rules.append((from_severity, after_seconds, to_severity))

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _dedup_hash(self, alert: Alert) -> str:
        return f"{alert.severity.value}:{alert.source}:{alert.title}"

    def send(self, severity: AlertSeverity, title: str, message: str, source: str = "system", channels: Optional[List[AlertChannel]] = None, metadata: Optional[Dict[str, Any]] = None) -> Alert:
        alert_id = f"{source}_{int(time.time() * 1000)}"
        alert = Alert(
            alert_id=alert_id,
            severity=severity,
            title=title,
            message=message,
            source=source,
            timestamp=time.time(),
            channels=channels or [AlertChannel.CONSOLE, AlertChannel.FILE],
            metadata=metadata or {},
        )
        # Deduplication
        h = self._dedup_hash(alert)
        now = time.time()
        if h in self._recent and now - self._recent[h] < self._dedup_window:
            return alert  # silently drop duplicate
        self._recent[h] = now
        # Clean old dedup entries
        self._recent = {k: v for k, v in self._recent.items() if now - v < self._dedup_window}
        # Dispatch
        self._alerts[alert_id] = alert
        for ch in alert.channels:
            handler = self._handlers.get(ch)
            if handler:
                try:
                    handler(alert)
                except Exception:
                    pass
            if ch == AlertChannel.WEBHOOK:
                self._webhook_handler(alert)
        # Save
        self._file_handler(alert)
        return alert

    def escalate(self, alert_id: str) -> bool:
        alert = self._alerts.get(alert_id)
        if not alert or alert.escalated:
            return False
        alert.escalated = True
        alert.severity = AlertSeverity.EMERGENCY if alert.severity == AlertSeverity.CRITICAL else AlertSeverity.CRITICAL
        self.send(alert.severity, f"[ESCALATED] {alert.title}", alert.message, alert.source, alert.channels, alert.metadata)
        return True

    def acknowledge(self, alert_id: str, user: str) -> bool:
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        alert.acknowledged = True
        alert.acknowledged_by = user
        return True

    # ------------------------------------------------------------------
    # Auto-escalation (call periodically)
    # ------------------------------------------------------------------

    def check_escalations(self) -> List[str]:
        escalated = []
        now = time.time()
        for alert in self._alerts.values():
            if alert.acknowledged or alert.escalated:
                continue
            for from_sev, after_s, to_sev in self._escalation_rules:
                if alert.severity == from_sev and now - alert.timestamp > after_s:
                    alert.escalated = True
                    alert.severity = to_sev
                    self.send(to_sev, f"[AUTO-ESCALATED] {alert.title}", alert.message, alert.source, alert.channels, alert.metadata)
                    escalated.append(alert.alert_id)
        return escalated

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        return self._alerts.get(alert_id)

    def list_alerts(self, severity: Optional[AlertSeverity] = None, acknowledged: Optional[bool] = None) -> List[Alert]:
        results = []
        for a in self._alerts.values():
            if severity and a.severity != severity:
                continue
            if acknowledged is not None and a.acknowledged != acknowledged:
                continue
            results.append(a)
        return sorted(results, key=lambda x: x.timestamp, reverse=True)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        by_severity: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        acked = 0
        for a in self._alerts.values():
            by_severity[a.severity.value] = by_severity.get(a.severity.value, 0) + 1
            by_source[a.source] = by_source.get(a.source, 0) + 1
            if a.acknowledged:
                acked += 1
        return {
            "total_alerts": len(self._alerts),
            "acknowledged": acked,
            "by_severity": by_severity,
            "by_source": by_source,
            "handlers": len(self._handlers),
            "escalation_rules": len(self._escalation_rules),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="magnatrix_alerts_")
    mgr = AlertNotificationManager(log_dir=tmp)
    print("=== Alert & Notification Demo ===\n")
    # Send alerts
    a1 = mgr.send(AlertSeverity.INFO, "System startup", "MAGNATRIX-OS is running", source="core")
    a2 = mgr.send(AlertSeverity.WARNING, "High CPU", "CPU usage above 80%", source="monitor", channels=[AlertChannel.CONSOLE])
    a3 = mgr.send(AlertSeverity.CRITICAL, "Safety breach", "Policy engine returned deny", source="governance")
    # Deduplicate test
    mgr.send(AlertSeverity.CRITICAL, "Safety breach", "Policy engine returned deny", source="governance")
    print(f"\nTotal alerts (dedup applied): {len(mgr._alerts)}")
    # Escalation
    mgr.add_escalation_rule(AlertSeverity.CRITICAL, 0.1, AlertSeverity.EMERGENCY)
    time.sleep(0.2)
    mgr.check_escalations()
    # Acknowledge
    mgr.acknowledge(a3.alert_id, "admin")
    print(f"Alert a3 acknowledged: {mgr.get_alert(a3.alert_id).acknowledged}")
    # Stats
    print(f"\nStats: {mgr.stats()}")
    # Cleanup
    import shutil
    shutil.rmtree(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
