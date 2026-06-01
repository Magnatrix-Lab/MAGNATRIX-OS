"""Analytics Dashboard — Token tracking, cost analysis, latency metrics, usage reports.

Modul ini menyediakan:
- MetricsCollector untuk pengumpulan real-time metrics
- TokenTracker untuk perhitungan token usage dan estimasi cost
- LatencyAnalyzer untuk response time analysis dan percentiles
- UsageReporter untuk aggregasi dan report generation
- CostEstimator untuk model pricing dan budget alerts

Arsitektur: Events → Collect → Aggregate → Report → Export
"""

from __future__ import annotations

import json
import time
import uuid
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto
from collections import defaultdict


class MetricType(Enum):
    COUNTER = auto()
    GAUGE = auto()
    HISTOGRAM = auto()
    TIMER = auto()


class AlertSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class MetricEvent:
    """Single metric event."""
    event_id: str
    metric_name: str
    metric_type: MetricType
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenUsage:
    """Token usage for a single request."""
    prompt_tokens: int
    completion_tokens: int
    model_id: str
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    thread_id: str = ""

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class CostRecord:
    """Cost record with pricing."""
    usage: TokenUsage
    cost_per_1k_prompt: float = 0.001
    cost_per_1k_completion: float = 0.003
    currency: str = "USD"

    @property
    def total_cost(self) -> float:
        prompt_cost = (self.usage.prompt_tokens / 1000) * self.cost_per_1k_prompt
        completion_cost = (self.usage.completion_tokens / 1000) * self.cost_per_1k_completion
        return round(prompt_cost + completion_cost, 6)


@dataclass
class LatencyRecord:
    """Latency measurement."""
    duration_ms: float
    model_id: str
    operation: str
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    thread_id: str = ""


@dataclass
class Alert:
    """Budget or performance alert."""
    alert_id: str
    severity: AlertSeverity
    message: str
    metric_name: str
    threshold: float
    actual_value: float
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


class MetricsCollector:
    """Collect and store real-time metrics."""

    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self._events: List[MetricEvent] = []
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)

    def record(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE,
               tags: Optional[Dict[str, str]] = None) -> MetricEvent:
        event = MetricEvent(
            event_id=str(uuid.uuid4())[:12],
            metric_name=name,
            metric_type=metric_type,
            value=value,
            timestamp=time.time(),
            tags=tags or {}
        )
        self._events.append(event)
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]

        if metric_type == MetricType.COUNTER:
            self._counters[name] += value
        elif metric_type == MetricType.GAUGE:
            self._gauges[name] = value
        elif metric_type == MetricType.HISTOGRAM:
            self._histograms[name].append(value)

        return event

    def counter(self, name: str, increment: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        self.record(name, increment, MetricType.COUNTER, tags)

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        self.record(name, value, MetricType.GAUGE, tags)

    def timer(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        self.record(name, duration_ms, MetricType.TIMER, tags)

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    def get_histogram(self, name: str) -> List[float]:
        return self._histograms.get(name, [])

    def get_events(self, name: Optional[str] = None, limit: int = 100) -> List[MetricEvent]:
        events = self._events
        if name:
            events = [e for e in events if e.metric_name == name]
        return events[-limit:]

    def get_stats(self, name: str) -> Dict[str, Any]:
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0}
        return {
            "count": len(values),
            "mean": round(sum(values) / len(values), 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "p50": round(self._percentile(values, 50), 4),
            "p95": round(self._percentile(values, 95), 4),
            "p99": round(self._percentile(values, 99), 4),
        }

    @staticmethod
    def _percentile(values: List[float], p: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


class TokenTracker:
    """Track token usage and estimate costs."""

    def __init__(self):
        self._usages: List[TokenUsage] = []
        self._model_pricing: Dict[str, Tuple[float, float]] = {
            "gpt-4": (0.03, 0.06),
            "gpt-3.5": (0.0015, 0.002),
            "llama-70b": (0.001, 0.003),
            "llama-7b": (0.0001, 0.0003),
        }

    def record(self, usage: TokenUsage) -> CostRecord:
        self._usages.append(usage)
        pricing = self._model_pricing.get(usage.model_id, (0.001, 0.003))
        return CostRecord(
            usage=usage,
            cost_per_1k_prompt=pricing[0],
            cost_per_1k_completion=pricing[1]
        )

    def set_pricing(self, model_id: str, prompt_price: float, completion_price: float) -> None:
        self._model_pricing[model_id] = (prompt_price, completion_price)

    def get_summary(self, model_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        usages = self._usages
        if model_id:
            usages = [u for u in usages if u.model_id == model_id]
        if user_id:
            usages = [u for u in usages if u.user_id == user_id]

        total_prompt = sum(u.prompt_tokens for u in usages)
        total_completion = sum(u.completion_tokens for u in usages)
        total_cost = sum(
            CostRecord(u, *self._model_pricing.get(u.model_id, (0.001, 0.003))).total_cost
            for u in usages
        )

        return {
            "total_requests": len(usages),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "estimated_cost": round(total_cost, 6),
            "currency": "USD"
        }

    def get_model_breakdown(self) -> Dict[str, Dict[str, Any]]:
        by_model = defaultdict(list)
        for u in self._usages:
            by_model[u.model_id].append(u)
        return {model: self._summarize(usages) for model, usages in by_model.items()}

    def _summarize(self, usages: List[TokenUsage]) -> Dict[str, Any]:
        total_prompt = sum(u.prompt_tokens for u in usages)
        total_completion = sum(u.completion_tokens for u in usages)
        total_cost = sum(
            CostRecord(u, *self._model_pricing.get(u.model_id, (0.001, 0.003))).total_cost
            for u in usages
        )
        return {
            "requests": len(usages),
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "cost": round(total_cost, 6)
        }


class LatencyAnalyzer:
    """Analyze response latency patterns."""

    def __init__(self):
        self._records: List[LatencyRecord] = []

    def record(self, record: LatencyRecord) -> None:
        self._records.append(record)

    def get_percentiles(self, model_id: Optional[str] = None, operation: Optional[str] = None) -> Dict[str, float]:
        records = self._records
        if model_id:
            records = [r for r in records if r.model_id == model_id]
        if operation:
            records = [r for r in records if r.operation == operation]
        durations = [r.duration_ms for r in records]
        if not durations:
            return {}
        return {
            "count": len(durations),
            "p50": round(self._percentile(durations, 50), 2),
            "p95": round(self._percentile(durations, 95), 2),
            "p99": round(self._percentile(durations, 99), 2),
            "mean": round(sum(durations) / len(durations), 2),
            "min": round(min(durations), 2),
            "max": round(max(durations), 2),
        }

    def get_trend(self, window_seconds: float = 3600.0) -> List[Dict[str, Any]]:
        now = time.time()
        recent = [r for r in self._records if now - r.timestamp <= window_seconds]
        if not recent:
            return []
        # Group by 5-minute buckets
        buckets = defaultdict(list)
        for r in recent:
            bucket = int(r.timestamp // 300) * 300
            buckets[bucket].append(r.duration_ms)
        return [
            {"timestamp": ts, "avg_latency": round(sum(vals) / len(vals), 2), "count": len(vals)}
            for ts, vals in sorted(buckets.items())
        ]

    @staticmethod
    def _percentile(values: List[float], p: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


class CostEstimator:
    """Estimate and monitor costs with budget alerts."""

    def __init__(self, budget: float = 100.0):
        self.budget = budget
        self._spent: float = 0.0
        self._alerts: List[Alert] = []
        self._alert_handlers: List[Callable[[Alert], None]] = []

    def add_cost(self, cost: float) -> None:
        self._spent += cost
        self._check_budget()

    def _check_budget(self) -> None:
        thresholds = [
            (0.5, AlertSeverity.INFO, "50% budget reached"),
            (0.8, AlertSeverity.WARNING, "80% budget reached"),
            (0.95, AlertSeverity.CRITICAL, "95% budget reached"),
        ]
        for pct, severity, msg in thresholds:
            if self._spent >= self.budget * pct:
                alert = Alert(
                    alert_id=str(uuid.uuid4())[:12],
                    severity=severity,
                    message=msg,
                    metric_name="budget_usage",
                    threshold=self.budget * pct,
                    actual_value=self._spent
                )
                self._alerts.append(alert)
                for handler in self._alert_handlers:
                    handler(alert)

    def on_alert(self, handler: Callable[[Alert], None]) -> None:
        self._alert_handlers.append(handler)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "budget": self.budget,
            "spent": round(self._spent, 6),
            "remaining": round(self.budget - self._spent, 6),
            "usage_percent": round(self._spent / self.budget * 100, 2),
            "alerts": len(self._alerts),
        }

    def get_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def set_budget(self, budget: float) -> None:
        self.budget = budget

    def reset(self) -> None:
        self._spent = 0.0
        self._alerts = []


class UsageReporter:
    """Generate comprehensive usage reports."""

    def __init__(self, metrics: MetricsCollector, tokens: TokenTracker,
                 latency: LatencyAnalyzer, costs: CostEstimator):
        self.metrics = metrics
        self.tokens = tokens
        self.latency = latency
        self.costs = costs

    def generate(self, period: str = "daily") -> Dict[str, Any]:
        return {
            "period": period,
            "generated_at": time.time(),
            "token_usage": self.tokens.get_summary(),
            "model_breakdown": self.tokens.get_model_breakdown(),
            "latency_percentiles": self.latency.get_percentiles(),
            "latency_trend": self.latency.get_trend(),
            "cost_summary": self.costs.get_summary(),
            "alerts": [
                {"severity": a.severity.name, "message": a.message, "actual": a.actual_value}
                for a in self.costs.get_alerts()
            ],
            "metrics": {
                "requests": self.metrics.get_counter("requests"),
                "errors": self.metrics.get_counter("errors"),
                "active_users": self.metrics.get_gauge("active_users"),
            }
        }

    def export_json(self, path: str, period: str = "daily") -> None:
        report = self.generate(period)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    def export_markdown(self, path: str, period: str = "daily") -> None:
        report = self.generate(period)
        lines = [
            f"# Usage Report — {period.title()}",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report['generated_at']))}",
            "",
            "## Token Usage",
            f"- Total Requests: {report['token_usage']['total_requests']}",
            f"- Total Tokens: {report['token_usage']['total_tokens']:,}",
            f"- Estimated Cost: ${report['token_usage']['estimated_cost']}",
            "",
            "## Model Breakdown",
        ]
        for model, stats in report['model_breakdown'].items():
            lines.append(f"- **{model}**: {stats['requests']} requests, ${stats['cost']}")
        lines.extend([
            "",
            "## Latency",
            f"- P50: {report['latency_percentiles'].get('p50', 'N/A')}ms",
            f"- P95: {report['latency_percentiles'].get('p95', 'N/A')}ms",
            f"- P99: {report['latency_percentiles'].get('p99', 'N/A')}ms",
            "",
            "## Cost & Alerts",
            f"- Budget: ${report['cost_summary']['budget']}",
            f"- Spent: ${report['cost_summary']['spent']}",
            f"- Usage: {report['cost_summary']['usage_percent']}%",
        ])
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


class AnalyticsDashboard:
    """End-to-end analytics dashboard."""

    def __init__(self, budget: float = 100.0):
        self.metrics = MetricsCollector()
        self.tokens = TokenTracker()
        self.latency = LatencyAnalyzer()
        self.costs = CostEstimator(budget)
        self.reporter = UsageReporter(self.metrics, self.tokens, self.latency, self.costs)
        self._alert_log: List[str] = []
        self.costs.on_alert(lambda a: self._alert_log.append(f"[{a.severity.name}] {a.message}"))

    def record_request(self, prompt_tokens: int, completion_tokens: int, model_id: str,
                       duration_ms: float, user_id: str = "", thread_id: str = "") -> None:
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_id=model_id,
            user_id=user_id,
            thread_id=thread_id
        )
        cost_record = self.tokens.record(usage)
        self.costs.add_cost(cost_record.total_cost)
        self.latency.record(LatencyRecord(
            duration_ms=duration_ms,
            model_id=model_id,
            operation="generate",
            user_id=user_id,
            thread_id=thread_id
        ))
        self.metrics.counter("requests")
        self.metrics.gauge("active_users", 1)

    def record_error(self, model_id: str) -> None:
        self.metrics.counter("errors")

    def get_report(self, period: str = "daily") -> Dict[str, Any]:
        return self.reporter.generate(period)

    def export(self, json_path: str, md_path: str, period: str = "daily") -> None:
        self.reporter.export_json(json_path, period)
        self.reporter.export_markdown(md_path, period)

    def get_alerts(self) -> List[str]:
        return self._alert_log

    def get_cost_summary(self) -> Dict[str, Any]:
        return self.costs.get_summary()


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("ANALYTICS DASHBOARD DEMO")
    print("=" * 70)

    dashboard = AnalyticsDashboard(budget=10.0)

    # 1. Simulate requests
    print("\n[1] Simulate Requests")
    requests = [
        (100, 50, "gpt-4", 250),
        (200, 100, "gpt-4", 300),
        (50, 30, "gpt-3.5", 120),
        (300, 150, "gpt-4", 450),
        (80, 40, "llama-7b", 200),
    ]
    for prompt_tok, comp_tok, model, latency in requests:
        dashboard.record_request(prompt_tok, comp_tok, model, latency, user_id="user-1")
    print(f"  Recorded {len(requests)} requests")

    # 2. Token summary
    print("\n[2] Token Summary")
    summary = dashboard.tokens.get_summary()
    print(f"  {summary}")

    # 3. Model breakdown
    print("\n[3] Model Breakdown")
    breakdown = dashboard.tokens.get_model_breakdown()
    for model, stats in breakdown.items():
        print(f"  {model}: {stats}")

    # 4. Latency analysis
    print("\n[4] Latency Analysis")
    percentiles = dashboard.latency.get_percentiles()
    print(f"  {percentiles}")
    trend = dashboard.latency.get_trend(window_seconds=3600)
    print(f"  Trend points: {len(trend)}")

    # 5. Cost tracking
    print("\n[5] Cost Tracking")
    cost = dashboard.get_cost_summary()
    print(f"  {cost}")

    # 6. Alerts
    print("\n[6] Budget Alerts")
    alerts = dashboard.get_alerts()
    for alert in alerts:
        print(f"  {alert}")

    # 7. Full report
    print("\n[7] Full Report")
    report = dashboard.get_report()
    print(f"  Requests: {report['metrics']['requests']}")
    print(f"  Errors: {report['metrics']['errors']}")
    print(f"  Total cost: ${report['token_usage']['estimated_cost']}")

    # 8. Export
    print("\n[8] Export Reports")
    dashboard.export("/tmp/analytics_report.json", "/tmp/analytics_report.md")
    with open("/tmp/analytics_report.md", "r") as f:
        md_content = f.read()
    print(f"  Markdown exported: {len(md_content)} chars")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
