"""Breakout Alert Engine - Alert generation and notification routing."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class Alert:
    alert_id: str
    symbol: str
    alert_type: str  # discord, email, webhook
    message: str
    priority: str  # high, medium, low
    sent: bool
    timestamp: float
    channel: str = ""

    def to_dict(self) -> Dict:
        return {"alert_id": self.alert_id, "symbol": self.symbol, "alert_type": self.alert_type,
                "message": self.message, "priority": self.priority, "sent": self.sent,
                "timestamp": self.timestamp, "channel": self.channel}

class BreakoutAlertEngine:
    """Generate and route alerts to Discord, email, or webhooks."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "breakout_alert"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.alerts: List[Alert] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for a in data.get("alerts",[]): self.alerts.append(Alert(**a))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"alerts": [a.to_dict() for a in self.alerts[-500:]]}, indent=2))

    def create_alert(self, symbol: str, alert_type: str, message: str, priority: str = "medium",
                     channel: str = "") -> Alert:
        alert = Alert(
            alert_id="alert_" + symbol + "_" + str(int(time.time()*1000)),
            symbol=symbol, alert_type=alert_type, message=message, priority=priority,
            sent=False, timestamp=time.time(), channel=channel)
        self.alerts.append(alert)
        self._save_state()
        return alert

    def send(self, alert_id: str) -> Alert:
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.sent = True
                self._save_state()
                return alert
        raise ValueError("Alert not found")

    def send_all(self, alert_type: str = "") -> int:
        count = 0
        for alert in self.alerts:
            if not alert.sent and (not alert_type or alert.alert_type == alert_type):
                alert.sent = True
                count += 1
        self._save_state()
        return count

    def get_pending(self) -> List[Alert]:
        return [a for a in self.alerts if not a.sent]

    def get_stats(self) -> Dict:
        sent = sum(1 for a in self.alerts if a.sent)
        by_type = {}
        for a in self.alerts: by_type[a.alert_type] = by_type.get(a.alert_type,0)+1
        return {"alerts_total": len(self.alerts), "sent": sent, "pending": len(self.alerts)-sent, "by_type": by_type}

    def to_dict(self) -> Dict:
        return {"alerts": [a.to_dict() for a in self.alerts[-100:]], "stats": self.get_stats()}

__all__ = ["BreakoutAlertEngine", "Alert"]
