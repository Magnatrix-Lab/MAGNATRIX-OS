"""Alerting Engine — threshold, anomaly, and rule-based alerts, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum, auto
import time

class AlertSeverity(Enum):
    INFO = auto()
    WARN = auto()
    CRITICAL = auto()

@dataclass
class AlertRule:
    rule_id: str
    name: str
    condition: Callable[[Any], bool]
    severity: AlertSeverity
    message_template: str
    cooldown: float = 60.0
    last_triggered: float = 0.0

@dataclass
class Alert:
    alert_id: str
    rule_id: str
    severity: AlertSeverity
    message: str
    timestamp: float
    value: Any

class AlertingEngine:
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.muted: List[str] = []

    def add_rule(self, rule: AlertRule):
        self.rules[rule.rule_id] = rule

    def evaluate(self, rule_id: str, value: Any) -> Optional[Alert]:
        rule = self.rules.get(rule_id)
        if not rule or rule_id in self.muted:
            return None
        now = time.time()
        if now - rule.last_triggered < rule.cooldown:
            return None
        try:
            triggered = rule.condition(value)
        except:
            return None
        if triggered:
            rule.last_triggered = now
            alert = Alert(str(len(self.alerts)), rule_id, rule.severity, rule.message_template.format(value=value), now, value)
            self.alerts.append(alert)
            return alert
        return None

    def evaluate_all(self, metrics: Dict[str, Any]) -> List[Alert]:
        triggered = []
        for rule_id, value in metrics.items():
            alert = self.evaluate(rule_id, value)
            if alert:
                triggered.append(alert)
        return triggered

    def mute(self, rule_id: str):
        self.muted.append(rule_id)

    def unmute(self, rule_id: str):
        self.muted = [m for m in self.muted if m != rule_id]

    def get_active(self, since: float = 0) -> List[Alert]:
        return [a for a in self.alerts if a.timestamp >= since]

    def stats(self) -> Dict:
        by_severity = {}
        for a in self.alerts:
            by_severity[a.severity.name] = by_severity.get(a.severity.name, 0) + 1
        return {"rules": len(self.rules), "alerts": len(self.alerts), "by_severity": by_severity, "muted": len(self.muted)}

def run():
    engine = AlertingEngine()
    engine.add_rule(AlertRule("cpu_high", "CPU > 80%", lambda v: v > 80, AlertSeverity.WARN, "CPU at {value}%"))
    engine.add_rule(AlertRule("disk_full", "Disk > 90%", lambda v: v > 90, AlertSeverity.CRITICAL, "Disk at {value}%"))
    metrics = {"cpu_high": 85, "disk_full": 95}
    alerts = engine.evaluate_all(metrics)
    for a in alerts:
        print(f"[{a.severity.name}] {a.message}")
    print(engine.stats())

if __name__ == "__main__":
    run()
