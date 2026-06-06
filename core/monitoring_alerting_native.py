#!/usr/bin/env python3
"""
Monitoring & Alerting Engine for MAGNATRIX-OS
Metrics collection, health checks, alerting, anomaly detection.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import math
import os
import threading
import time
import urllib.request
import urllib.error
import smtplib
from email.mime.text import MIMEText
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class MetricType(enum.Enum):
    COUNTER = "counter"    # Monotonically increasing
    GAUGE = "gauge"        # Can go up or down
    HISTOGRAM = "histogram"  # Distribution of values


class AlertSeverity(enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class HealthStatus(enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclasses.dataclass
class MetricPoint:
    timestamp: float
    value: float
    tags: Dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class AlertRule:
    name: str
    metric: str
    condition: str  # ">", "<", "==", "range", "rate", "absence"
    threshold: float
    threshold_high: Optional[float] = None  # For range
    duration: int = 0  # Seconds condition must persist
    severity: AlertSeverity = AlertSeverity.WARNING
    cooldown: int = 300  # Seconds between repeated alerts
    channels: List[str] = dataclasses.field(default_factory=list)
    last_fired: float = 0.0
    enabled: bool = True


@dataclasses.dataclass
class Alert:
    rule_name: str
    severity: AlertSeverity
    message: str
    metric_value: float
    timestamp: float
    tags: Dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class HealthCheck:
    name: str
    check_type: str  # "http", "tcp", "process", "file", "custom"
    target: str
    interval: int = 30
    timeout: int = 5
    retries: int = 2
    enabled: bool = True
    last_status: HealthStatus = HealthStatus.HEALTHY
    last_check: float = 0.0
    last_error: Optional[str] = None
    consecutive_failures: int = 0


class MetricsCollector:
    """Collect and store time-series metrics."""

    def __init__(self, max_points: int = 10000) -> None:
        self._metrics: Dict[str, List[MetricPoint]] = {}
        self._metadata: Dict[str, MetricType] = {}
        self._max_points = max_points
        self._lock = threading.Lock()

    def register(self, name: str, metric_type: MetricType) -> None:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
                self._metadata[name] = metric_type

    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
                self._metadata[name] = MetricType.GAUGE

            point = MetricPoint(timestamp=time.time(), value=value, tags=tags or {})
            self._metrics[name].append(point)

            # Trim old points
            if len(self._metrics[name]) > self._max_points:
                self._metrics[name] = self._metrics[name][-self._max_points:]

    def counter(self, name: str, increment: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
                self._metadata[name] = MetricType.COUNTER

            current = self._metrics[name][-1].value if self._metrics[name] else 0.0
            point = MetricPoint(timestamp=time.time(), value=current + increment, tags=tags or {})
            self._metrics[name].append(point)

    def get(self, name: str, window: int = 3600) -> List[MetricPoint]:
        """Get metrics from last N seconds."""
        with self._lock:
            points = self._metrics.get(name, [])
            cutoff = time.time() - window
            return [p for p in points if p.timestamp >= cutoff]

    def latest(self, name: str) -> Optional[float]:
        with self._lock:
            points = self._metrics.get(name, [])
            return points[-1].value if points else None

    def avg(self, name: str, window: int = 3600) -> Optional[float]:
        points = self.get(name, window)
        if not points:
            return None
        return sum(p.value for p in points) / len(points)

    def max_val(self, name: str, window: int = 3600) -> Optional[float]:
        points = self.get(name, window)
        return max(p.value for p in points) if points else None

    def min_val(self, name: str, window: int = 3600) -> Optional[float]:
        points = self.get(name, window)
        return min(p.value for p in points) if points else None

    def list_metrics(self) -> List[str]:
        with self._lock:
            return list(self._metrics.keys())

    def moving_average(self, name: str, window_size: int = 10) -> Optional[float]:
        points = self._metrics.get(name, [])
        if len(points) < window_size:
            return None
        recent = points[-window_size:]
        return sum(p.value for p in recent) / len(recent)

    def ema(self, name: str, alpha: float = 0.3) -> Optional[float]:
        """Exponential moving average."""
        points = self._metrics.get(name, [])
        if not points:
            return None
        ema = points[0].value
        for p in points[1:]:
            ema = alpha * p.value + (1 - alpha) * ema
        return ema

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                name: {
                    "type": self._metadata[name].value,
                    "count": len(points),
                    "latest": points[-1].value if points else None,
                    "avg": sum(p.value for p in points) / len(points) if points else None,
                }
                for name, points in self._metrics.items()
            }


class AlertEngine:
    """Evaluate alert rules and trigger notifications."""

    def __init__(self, metrics: MetricsCollector) -> None:
        self._metrics = metrics
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: List[Alert] = []
        self._lock = threading.Lock()

    def add_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self._rules[rule.name] = rule

    def evaluate(self) -> List[Alert]:
        """Evaluate all rules and return fired alerts."""
        fired = []
        with self._lock:
            for rule in self._rules.values():
                if not rule.enabled:
                    continue

                # Check cooldown
                if time.time() - rule.last_fired < rule.cooldown:
                    continue

                latest = self._metrics.latest(rule.metric)
                if latest is None:
                    continue

                triggered = False
                message = ""

                if rule.condition == ">":
                    triggered = latest > rule.threshold
                    message = f"{rule.metric} = {latest:.2f} > {rule.threshold}"
                elif rule.condition == "<":
                    triggered = latest < rule.threshold
                    message = f"{rule.metric} = {latest:.2f} < {rule.threshold}"
                elif rule.condition == "==":
                    triggered = latest == rule.threshold
                    message = f"{rule.metric} = {latest:.2f} == {rule.threshold}"
                elif rule.condition == "range":
                    if rule.threshold_high is not None:
                        triggered = latest < rule.threshold or latest > rule.threshold_high
                        message = f"{rule.metric} = {latest:.2f} outside [{rule.threshold}, {rule.threshold_high}]"
                elif rule.condition == "rate":
                    points = self._metrics.get(rule.metric, 300)
                    if len(points) >= 2:
                        rate = (points[-1].value - points[0].value) / max(1, points[-1].timestamp - points[0].timestamp)
                        triggered = abs(rate) > rule.threshold
                        message = f"{rule.metric} rate = {rate:.2f}/s > {rule.threshold}"

                if triggered:
                    alert = Alert(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=message,
                        metric_value=latest,
                        timestamp=time.time(),
                    )
                    fired.append(alert)
                    self._alerts.append(alert)
                    rule.last_fired = time.time()

        return fired

    def get_alerts(self, limit: int = 100) -> List[Alert]:
        with self._lock:
            return self._alerts[-limit:]

    def clear_alerts(self) -> None:
        with self._lock:
            self._alerts.clear()


class HealthCheckEngine:
    """Run health checks and report status."""

    def __init__(self) -> None:
        self._checks: Dict[str, HealthCheck] = {}
        self._lock = threading.Lock()

    def add(self, check: HealthCheck) -> None:
        with self._lock:
            self._checks[check.name] = check

    def run_check(self, check: HealthCheck) -> HealthStatus:
        try:
            if check.check_type == "http":
                req = urllib.request.Request(check.target, method="HEAD", timeout=check.timeout)
                with urllib.request.urlopen(req) as resp:
                    status = HealthStatus.HEALTHY if resp.status < 400 else HealthStatus.UNHEALTHY
            elif check.check_type == "tcp":
                import socket
                host, port = check.target.split(":")
                with socket.create_connection((host, int(port)), timeout=check.timeout):
                    status = HealthStatus.HEALTHY
            elif check.check_type == "process":
                import subprocess
                result = subprocess.run(["pgrep", "-f", check.target], capture_output=True, timeout=check.timeout)
                status = HealthStatus.HEALTHY if result.returncode == 0 else HealthStatus.UNHEALTHY
            elif check.check_type == "file":
                status = HealthStatus.HEALTHY if os.path.exists(check.target) else HealthStatus.UNHEALTHY
            else:
                status = HealthStatus.HEALTHY

            check.last_status = status
            check.last_error = None
            check.consecutive_failures = 0

        except Exception as exc:
            check.consecutive_failures += 1
            check.last_error = str(exc)
            if check.consecutive_failures >= check.retries:
                check.last_status = HealthStatus.UNHEALTHY
            else:
                check.last_status = HealthStatus.DEGRADED

        check.last_check = time.time()
        return check.last_status

    def run_all(self) -> Dict[str, HealthStatus]:
        results = {}
        with self._lock:
            for check in self._checks.values():
                if check.enabled:
                    results[check.name] = self.run_check(check)
        return results

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._checks)
            healthy = sum(1 for c in self._checks.values() if c.last_status == HealthStatus.HEALTHY)
            degraded = sum(1 for c in self._checks.values() if c.last_status == HealthStatus.DEGRADED)
            unhealthy = sum(1 for c in self._checks.values() if c.last_status == HealthStatus.UNHEALTHY)
            return {
                "total": total,
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
                "overall": HealthStatus.HEALTHY.value if unhealthy == 0 else (HealthStatus.DEGRADED.value if unhealthy < total // 2 else HealthStatus.UNHEALTHY.value),
                "checks": {
                    name: {
                        "status": c.last_status.value,
                        "last_check": c.last_check,
                        "error": c.last_error,
                    }
                    for name, c in self._checks.items()
                },
            }


class AnomalyDetector:
    """Simple anomaly detection on metrics."""

    def __init__(self, metrics: MetricsCollector) -> None:
        self._metrics = metrics

    def z_score(self, name: str, window: int = 3600) -> Optional[float]:
        points = self._metrics.get(name, window)
        if len(points) < 2:
            return None
        values = [p.value for p in points]
        mean = sum(values) / len(values)
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
        if std == 0:
            return 0.0
        latest = values[-1]
        return (latest - mean) / std

    def trend_slope(self, name: str, window: int = 3600) -> Optional[float]:
        points = self._metrics.get(name, window)
        if len(points) < 2:
            return None
        n = len(points)
        x = [p.timestamp for p in points]
        y = [p.value for p in points]
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        return numerator / denominator if denominator != 0 else 0.0

    def detect_spike(self, name: str, threshold: float = 3.0) -> bool:
        z = self.z_score(name)
        return z is not None and abs(z) > threshold


class NotificationChannel:
    """Base class for notification channels."""

    def send(self, alert: Alert) -> bool:
        raise NotImplementedError


class ConsoleChannel(NotificationChannel):
    def send(self, alert: Alert) -> bool:
        print(f"[ALERT {alert.severity.value.upper()}] {alert.rule_name}: {alert.message}")
        return True


class FileChannel(NotificationChannel):
    def __init__(self, path: str) -> None:
        self._path = path

    def send(self, alert: Alert) -> bool:
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps({
                    "timestamp": alert.timestamp,
                    "rule": alert.rule_name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "value": alert.metric_value,
                }) + "\n")
            return True
        except Exception:
            return False


class WebhookChannel(NotificationChannel):
    def __init__(self, url: str) -> None:
        self._url = url

    def send(self, alert: Alert) -> bool:
        try:
            body = json.dumps({
                "rule": alert.rule_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "value": alert.metric_value,
                "timestamp": alert.timestamp,
            }).encode("utf-8")
            req = urllib.request.Request(
                self._url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status < 400
        except Exception:
            return False


class EmailChannel(NotificationChannel):
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, from_addr: str, to_addrs: List[str]) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._from_addr = from_addr
        self._to_addrs = to_addrs

    def send(self, alert: Alert) -> bool:
        try:
            msg = MIMEText(f"ALERT: {alert.rule_name}\nSeverity: {alert.severity.value}\nMessage: {alert.message}\nValue: {alert.metric_value}\nTime: {time.ctime(alert.timestamp)}")
            msg["Subject"] = f"[MAGNATRIX-OS] {alert.severity.value.upper()}: {alert.rule_name}"
            msg["From"] = self._from_addr
            msg["To"] = ", ".join(self._to_addrs)

            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._username, self._password)
                server.send_message(msg)
            return True
        except Exception:
            return False


class MonitoringEngine:
    """Main monitoring orchestrator."""

    def __init__(self) -> None:
        self.metrics = MetricsCollector()
        self.alerts = AlertEngine(self.metrics)
        self.health = HealthCheckEngine()
        self.anomaly = AnomalyDetector(self.metrics)
        self._channels: Dict[str, NotificationChannel] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_channel(self, name: str, channel: NotificationChannel) -> None:
        self._channels[name] = channel

    def start(self, interval: int = 10) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _run_loop(self, interval: int) -> None:
        while self._running:
            # Run health checks
            self.health.run_all()

            # Evaluate alerts
            fired = self.alerts.evaluate()
            for alert in fired:
                for channel in self._channels.values():
                    channel.send(alert)

            time.sleep(interval)

    def get_dashboard_data(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics.to_dict(),
            "health": self.health.get_summary(),
            "alerts": [
                {
                    "rule": a.rule_name,
                    "severity": a.severity.value,
                    "message": a.message,
                    "value": a.metric_value,
                    "time": a.timestamp,
                }
                for a in self.alerts.get_alerts(20)
            ],
            "timestamp": time.time(),
        }

    def save(self, path: str) -> None:
        data = self.get_dashboard_data()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== MAGNATRIX-OS Monitoring & Alerting Engine Demo ===\n")

    engine = MonitoringEngine()
    engine.add_channel("console", ConsoleChannel())

    # Register metrics
    engine.metrics.register("cpu_usage", MetricType.GAUGE)
    engine.metrics.register("memory_usage", MetricType.GAUGE)
    engine.metrics.register("disk_usage", MetricType.GAUGE)
    engine.metrics.register("requests_total", MetricType.COUNTER)

    # Simulate metrics
    import random
    for i in range(20):
        engine.metrics.record("cpu_usage", 30 + random.random() * 40)
        engine.metrics.record("memory_usage", 40 + random.random() * 30)
        engine.metrics.record("disk_usage", 50 + i * 2)
        engine.metrics.counter("requests_total", 100)

    # Add alert rules
    engine.alerts.add_rule(AlertRule(
        name="high_cpu",
        metric="cpu_usage",
        condition=">",
        threshold=60.0,
        severity=AlertSeverity.CRITICAL,
        cooldown=5,
    ))
    engine.alerts.add_rule(AlertRule(
        name="high_memory",
        metric="memory_usage",
        condition=">",
        threshold=65.0,
        severity=AlertSeverity.WARNING,
        cooldown=5,
    ))
    engine.alerts.add_rule(AlertRule(
        name="disk_full",
        metric="disk_usage",
        condition=">",
        threshold=85.0,
        severity=AlertSeverity.EMERGENCY,
        cooldown=5,
    ))

    # Evaluate alerts
    print("--- Alert Evaluation ---")
    fired = engine.alerts.evaluate()
    print(f"Fired alerts: {len(fired)}\n")

    # Health checks
    print("--- Health Checks ---")
    engine.health.add(HealthCheck(name="web", check_type="tcp", target="127.0.0.1:8765", timeout=1))
    engine.health.add(HealthCheck(name="files", check_type="file", target="/tmp"))
    results = engine.health.run_all()
    for name, status in results.items():
        print(f"  {name}: {status.value}")
    print()

    # Anomaly detection
    print("--- Anomaly Detection ---")
    z_cpu = engine.anomaly.z_score("cpu_usage")
    z_disk = engine.anomaly.z_score("disk_usage")
    trend = engine.anomaly.trend_slope("disk_usage")
    print(f"  CPU z-score: {z_cpu:.2f if z_cpu else 'N/A'}")
    print(f"  Disk z-score: {z_disk:.2f if z_disk else 'N/A'}")
    print(f"  Disk trend: {trend:.2f if trend else 'N/A'} units/sec")
    print()

    # Dashboard data
    print("--- Dashboard Summary ---")
    dash = engine.get_dashboard_data()
    print(f"  Metrics tracked: {len(dash['metrics'])}")
    print(f"  Health overall: {dash['health']['overall']}")
    print(f"  Recent alerts: {len(dash['alerts'])}")
    print()

    print("=== Monitoring Engine Demo Complete ===")


if __name__ == "__main__":
    _demo()
