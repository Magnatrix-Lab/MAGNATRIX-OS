"""
MAGNATRIX-OS Monitoring & Observability System
Self-contained native monitoring with metrics, alerts, health integration,
dashboard data, log aggregation, trace propagation, and SLA calculation.
"""

import time, json, threading, statistics
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque


@dataclass
class Metric:
    """Single metric sample."""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Threshold-based alert rule."""
    name: str
    metric: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    duration_sec: int = 0
    labels: Dict[str, str] = field(default_factory=dict)


class MonitoringSystem:
    """Monitoring and observability for MAGNATRIX-OS."""

    def __init__(self, retention_sec: int = 3600):
        self.retention = retention_sec
        self._counters: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"value": 0, "labels": {}})
        self._gauges: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"value": 0.0, "labels": {}})
        self._histograms: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"buckets": deque(maxlen=10000), "labels": {}}
        )
        self._metrics: deque = deque(maxlen=50000)
        self._rules: Dict[str, AlertRule] = {}
        self._alert_state: Dict[str, Dict] = {}
        self._notifications: List[Dict] = []
        self._webhooks: List[str] = []
        self._logs: deque = deque(maxlen=10000)
        self._traces: deque = deque(maxlen=5000)
        self._health_checks: Dict[str, Callable] = {}
        self._slas: Dict[str, Dict] = defaultdict(lambda: {"total": 0, "ok": 0, "samples": deque(maxlen=1000)})
        self._lock = threading.Lock()

    # ── metrics collection ──────────────────────────────────────

    def counter(self, name: str, increment: int = 1, labels: Dict = None) -> None:
        with self._lock:
            self._counters[name]["value"] += increment
            if labels:
                self._counters[name]["labels"].update(labels)
            self._metrics.append(Metric(name, self._counters[name]["value"], time.time(), labels or {}))

    def gauge(self, name: str, value: float, labels: Dict = None) -> None:
        with self._lock:
            self._gauges[name]["value"] = value
            if labels:
                self._gauges[name]["labels"].update(labels)
            self._metrics.append(Metric(name, value, time.time(), labels or {}))

    def histogram(self, name: str, value: float, labels: Dict = None) -> None:
        with self._lock:
            self._histograms[name]["buckets"].append(value)
            if labels:
                self._histograms[name]["labels"].update(labels)
            self._metrics.append(Metric(name, value, time.time(), labels or {}))

    def metric_summary(self, name: str, kind: str = "counter") -> Dict:
        with self._lock:
            if kind == "counter":
                d = self._counters.get(name, {})
                return {"name": name, "kind": "counter", "value": d.get("value", 0), "labels": d.get("labels", {})}
            elif kind == "gauge":
                d = self._gauges.get(name, {})
                return {"name": name, "kind": "gauge", "value": d.get("value", 0), "labels": d.get("labels", {})}
            elif kind == "histogram":
                d = self._histograms.get(name, {})
                vals = list(d.get("buckets", []))
                if not vals:
                    return {"name": name, "kind": "histogram", "count": 0, "labels": d.get("labels", {})}
                return {"name": name, "kind": "histogram", "count": len(vals),
                        "avg": statistics.mean(vals), "median": statistics.median(vals),
                        "p95": self._percentile(vals, 95), "p99": self._percentile(vals, 99),
                        "min": min(vals), "max": max(vals), "labels": d.get("labels", {})}
        return {}

    def _percentile(self, data: List[float], p: float) -> float:
        s = sorted(data)
        k = (len(s) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(s) else f
        return s[f] + (k - f) * (s[c] - s[f]) if f != c else s[f]

    # ── alert rules ───────────────────────────────────────────

    def add_alert_rule(self, rule: AlertRule) -> None:
        self._rules[rule.name] = rule

    def remove_alert_rule(self, name: str) -> None:
        if name in self._rules:
            del self._rules[name]
            self._alert_state.pop(name, None)

    def check_alerts(self) -> List[Dict]:
        triggered = []
        now = time.time()
        with self._lock:
            for name, rule in self._rules.items():
                val = self._get_metric_value(rule.metric)
                fired = self._eval_condition(val, rule.condition, rule.threshold)
                state = self._alert_state.get(name)
                if fired:
                    if state is None:
                        self._alert_state[name] = {"first_seen": now, "firing": True}
                    elif now - state["first_seen"] >= rule.duration_sec:
                        if not state.get("notified"):
                            triggered.append({"rule": name, "metric": rule.metric,
                                              "value": val, "threshold": rule.threshold,
                                              "condition": rule.condition})
                            state["notified"] = True
                            self._notify(name, val, rule)
                else:
                    self._alert_state.pop(name, None)
        return triggered

    def _get_metric_value(self, metric: str) -> float:
        if metric in self._gauges:
            return self._gauges[metric]["value"]
        if metric in self._counters:
            return self._counters[metric]["value"]
        if metric in self._histograms:
            vals = list(self._histograms[metric]["buckets"])
            return statistics.mean(vals) if vals else 0.0
        return 0.0

    def _eval_condition(self, val: float, cond: str, threshold: float) -> bool:
        return {
            "gt": val > threshold, "lt": val < threshold, "eq": val == threshold,
            "gte": val >= threshold, "lte": val <= threshold,
        }.get(cond, False)

    # ── notifications ───────────────────────────────────────────

    def add_webhook(self, url: str) -> None:
        self._webhooks.append(url)

    def _notify(self, rule_name: str, value: float, rule: AlertRule) -> None:
        payload = {
            "alert": rule_name, "metric": rule.metric, "value": value,
            "threshold": rule.threshold, "condition": rule.condition,
            "timestamp": datetime.now().isoformat()
        }
        self._notifications.append(payload)
        # webhook simulation
        for url in self._webhooks:
            self._notifications.append({"webhook": url, "payload": payload, "status": "simulated"})
        # email simulation
        self._notifications.append({
            "email": "admin@matrix.local", "subject": f"ALERT: {rule_name}",
            "body": json.dumps(payload, indent=2), "status": "simulated"
        })

    def notifications(self, limit: int = 100) -> List[Dict]:
        return self._notifications[-limit:]

    # ── health check integration ──────────────────────────────

    def register_health_check(self, name: str, fn: Callable[[], Dict]) -> None:
        self._health_checks[name] = fn

    def health(self) -> Dict:
        result = {"overall": "ok", "checks": {}}
        for name, fn in self._health_checks.items():
            try:
                check = fn()
                result["checks"][name] = check
                if check.get("ok") is False:
                    result["overall"] = "degraded"
            except Exception as e:
                result["checks"][name] = {"ok": False, "error": str(e)}
                result["overall"] = "degraded"
        return result

    # ── dashboard data ──────────────────────────────────────────

    def dashboard(self) -> Dict:
        with self._lock:
            return {
                "counters": {k: v["value"] for k, v in self._counters.items()},
                "gauges": {k: v["value"] for k, v in self._gauges.items()},
                "histograms": {k: self.metric_summary(k, "histogram") for k in self._histograms},
                "alerts": list(self._alert_state.keys()),
                "health": self.health(),
                "timestamp": datetime.now().isoformat()
            }

    # ── log aggregation ────────────────────────────────────────

    def log(self, level: str, message: str, extra: Dict = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(), "level": level,
            "message": message, "extra": extra or {}
        }
        self._logs.append(entry)

    def logs(self, level: str = "", limit: int = 100) -> List[Dict]:
        out = list(self._logs)
        if level:
            out = [e for e in out if e["level"] == level]
        return out[-limit:]

    def search_logs(self, query: str) -> List[Dict]:
        return [e for e in self._logs if query.lower() in e["message"].lower()]

    # ── trace propagation ───────────────────────────────────────

    def start_trace(self, name: str, trace_id: str = "", parent_id: str = "") -> str:
        tid = trace_id or f"{name}-{time.time():.6f}"
        span = {
            "trace_id": tid, "span_id": f"{tid}-{time.time():.6f}",
            "parent_id": parent_id, "name": name,
            "start": time.time(), "end": None, "logs": []
        }
        self._traces.append(span)
        return span["span_id"]

    def end_trace(self, span_id: str) -> None:
        for span in self._traces:
            if span["span_id"] == span_id:
                span["end"] = time.time()
                break

    def add_trace_log(self, span_id: str, event: str, data: Dict = None) -> None:
        for span in self._traces:
            if span["span_id"] == span_id:
                span["logs"].append({"time": time.time(), "event": event, "data": data or {}})
                break

    def traces(self, trace_id: str = "") -> List[Dict]:
        out = list(self._traces)
        if trace_id:
            out = [t for t in out if t["trace_id"] == trace_id]
        return out

    # ── SLA calculation ─────────────────────────────────────────

    def record_sla(self, service: str, success: bool, latency_ms: float = 0) -> None:
        self._slas[service]["total"] += 1
        if success:
            self._slas[service]["ok"] += 1
        self._slas[service]["samples"].append(latency_ms)

    def sla(self, service: str) -> Dict:
        s = self._slas[service]
        total = s["total"]
        ok = s["ok"]
        samples = list(s["samples"])
        return {
            "service": service, "total": total, "ok": ok,
            "availability_pct": (ok / total * 100) if total else 0,
            "avg_latency_ms": statistics.mean(samples) if samples else 0,
            "p95_latency_ms": self._percentile(samples, 95) if samples else 0,
            "p99_latency_ms": self._percentile(samples, 99) if samples else 0,
        }

    def all_slas(self) -> Dict[str, Dict]:
        return {k: self.sla(k) for k in self._slas}


# ── self-test ─────────────────────────────────────────────────

def _self_test():
    mon = MonitoringSystem(retention_sec=60)

    # counter
    mon.counter("requests", 10)
    mon.counter("requests", 5)
    assert mon.metric_summary("requests", "counter")["value"] == 15

    # gauge
    mon.gauge("cpu_usage", 45.5)
    assert mon.metric_summary("cpu_usage", "gauge")["value"] == 45.5

    # histogram
    for i in range(100):
        mon.histogram("latency", float(i))
    h = mon.metric_summary("latency", "histogram")
    assert h["count"] == 100
    assert h["p95"] >= 94

    # alert rule
    mon.add_alert_rule(AlertRule("high_cpu", "cpu_usage", "gt", 80, duration_sec=0))
    mon.gauge("cpu_usage", 85.0)
    alerts = mon.check_alerts()
    assert len(alerts) == 1 and alerts[0]["rule"] == "high_cpu"

    # health check
    mon.register_health_check("db", lambda: {"ok": True, "latency_ms": 5})
    h = mon.health()
    assert h["overall"] == "ok"
    assert h["checks"]["db"]["ok"] is True

    # logs
    mon.log("INFO", "system started")
    mon.log("ERROR", "something failed")
    assert len(mon.logs("ERROR")) == 1
    assert len(mon.search_logs("started")) == 1

    # trace
    sid = mon.start_trace("request", trace_id="t1")
    mon.add_trace_log(sid, "processing")
    mon.end_trace(sid)
    assert len(mon.traces("t1")) >= 1

    # SLA
    for _ in range(100):
        mon.record_sla("api", success=True, latency_ms=50.0)
    mon.record_sla("api", success=False, latency_ms=0.0)
    s = mon.sla("api")
    assert s["availability_pct"] >= 99.0
    assert s["avg_latency_ms"] == 50.0

    # dashboard
    db = mon.dashboard()
    assert "counters" in db and "gauges" in db
    assert db["alerts"] == ["high_cpu"]

    # notifications
    assert len(mon.notifications()) > 0

    print("[monitoring_native] all tests passed")


if __name__ == "__main__":
    _self_test()
