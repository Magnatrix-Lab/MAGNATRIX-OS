"""Observability & LLM-as-a-Judge — Metrics, tracing, evaluation, and monitoring.

Modul ini menyediakan:
- MetricsCollector untuk request latency, token usage, error rates, throughput
- Tracer untuk distributed tracing dengan span tree
- LLMJudge untuk automated evaluation dengan rubric-based scoring
- CostMonitor untuk real-time cost tracking dan alerting
- AlertManager untuk threshold-based alerting
- ObservabilityDashboard untuk aggregated metrics view

Berdasarkan: production-grade-agentic-system observability layer (FareedKhan-dev)
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


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
class Metric:
    """Single metric data point."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class Span:
    """Distributed tracing span."""
    span_id: str
    trace_id: str
    parent_id: Optional[str]
    name: str
    start_time: float
    end_time: float = 0.0
    status: str = "ok"  # ok, error, timeout
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)

    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time > 0 else time.time() - self.start_time


@dataclass
class Alert:
    """Alert triggered by threshold violation."""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    threshold: float
    actual_value: float
    timestamp: float
    acknowledged: bool = False


class MetricsCollector:
    """Collect and aggregate metrics."""

    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self._metrics: List[Metric] = []
        self._aggregates: Dict[str, Dict[str, Any]] = {}

    def record(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE,
               labels: Optional[Dict[str, str]] = None, unit: str = "") -> None:
        m = Metric(name, value, metric_type, time.time(), labels or {}, unit)
        self._metrics.append(m)
        if len(self._metrics) > self.max_points:
            self._metrics = self._metrics[-self.max_points:]
        self._update_aggregate(name, value, metric_type)

    def _update_aggregate(self, name: str, value: float, metric_type: MetricType) -> None:
        agg = self._aggregates.setdefault(name, {"count": 0, "sum": 0.0, "min": float('inf'), "max": 0.0, "last": 0.0})
        agg["count"] += 1
        agg["sum"] += value
        agg["min"] = min(agg["min"], value)
        agg["max"] = max(agg["max"], value)
        agg["last"] = value
        agg["avg"] = agg["sum"] / agg["count"]

    def get_aggregate(self, name: str) -> Dict[str, Any]:
        return self._aggregates.get(name, {})

    def get_recent(self, name: Optional[str] = None, n: int = 100) -> List[Metric]:
        metrics = self._metrics
        if name:
            metrics = [m for m in metrics if m.name == name]
        return metrics[-n:]

    def get_all_aggregates(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._aggregates)

    def timer(self, name: str, labels: Optional[Dict[str, str]] = None) -> "TimerContext":
        return TimerContext(self, name, labels)

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "aggregates": self._aggregates,
                "recent_count": len(self._metrics),
            }, f, indent=2)


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, name: str, labels: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.labels = labels or {}
        self.start = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        duration = time.time() - self.start
        self.collector.record(self.name, duration, MetricType.TIMER, self.labels, "seconds")


class Tracer:
    """Distributed tracing with span tree."""

    def __init__(self):
        self._spans: Dict[str, Span] = {}
        self._traces: Dict[str, List[str]] = {}  # trace_id -> list of span_ids

    def start_span(self, name: str, trace_id: Optional[str] = None,
                   parent_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Span:
        span = Span(
            span_id=str(uuid.uuid4())[:12],
            trace_id=trace_id or str(uuid.uuid4())[:12],
            parent_id=parent_id,
            name=name,
            start_time=time.time(),
            metadata=metadata or {},
        )
        self._spans[span.span_id] = span
        self._traces.setdefault(span.trace_id, []).append(span.span_id)
        if parent_id and parent_id in self._spans:
            self._spans[parent_id].children.append(span.span_id)
        return span

    def end_span(self, span_id: str, status: str = "ok") -> None:
        span = self._spans.get(span_id)
        if span:
            span.end_time = time.time()
            span.status = status

    def get_trace(self, trace_id: str) -> List[Span]:
        span_ids = self._traces.get(trace_id, [])
        return [self._spans[sid] for sid in span_ids if sid in self._spans]

    def get_span_tree(self, trace_id: str) -> Dict[str, Any]:
        spans = self.get_trace(trace_id)
        if not spans:
            return {}
        root = [s for s in spans if s.parent_id is None]
        if not root:
            return {}

        def build_tree(span: Span) -> Dict[str, Any]:
            return {
                "span_id": span.span_id,
                "name": span.name,
                "duration": round(span.duration(), 3),
                "status": span.status,
                "children": [build_tree(self._spans[cid]) for cid in span.children if cid in self._spans],
            }

        return build_tree(root[0])

    def get_stats(self) -> Dict[str, Any]:
        total_spans = len(self._spans)
        total_traces = len(self._traces)
        durations = [s.duration() for s in self._spans.values() if s.end_time > 0]
        return {
            "total_spans": total_spans,
            "total_traces": total_traces,
            "avg_duration": sum(durations) / max(len(durations), 1),
            "max_duration": max(durations) if durations else 0,
            "error_spans": sum(1 for s in self._spans.values() if s.status == "error"),
        }


class LLMJudge:
    """Automated evaluation using rubric-based scoring."""

    def __init__(self):
        self._rubrics: Dict[str, List[Tuple[str, float, Callable[[str, str], float]]]] = {}

    def add_rubric(self, task_type: str, criteria: List[Tuple[str, float, Callable[[str, str], float]]]) -> None:
        self._rubrics[task_type] = criteria

    def evaluate(self, prompt: str, response: str, task_type: str = "general") -> Dict[str, Any]:
        criteria = self._rubrics.get(task_type, self._default_rubric())
        scores = {}
        total_weight = sum(w for _, w, _ in criteria)
        weighted_score = 0.0

        for name, weight, scorer in criteria:
            s = scorer(prompt, response)
            scores[name] = round(s, 3)
            weighted_score += s * (weight / total_weight)

        return {
            "overall_score": round(weighted_score, 3),
            "scores": scores,
            "task_type": task_type,
            "verdict": "pass" if weighted_score >= 0.6 else "fail",
        }

    def _default_rubric(self) -> List[Tuple[str, float, Callable[[str, str], float]]]:
        return [
            ("relevance", 1.0, lambda p, r: self._overlap_score(p, r)),
            ("coherence", 1.0, lambda p, r: 1.0 if len(r) > 20 and "." in r else 0.3),
            ("completeness", 1.0, lambda p, r: min(1.0, len(r) / 100)),
            ("correctness", 1.0, lambda p, r: 0.8 if any(k in r.lower() for k in ["correct", "answer", "result"]) else 0.5),
        ]

    @staticmethod
    def _overlap_score(prompt: str, response: str) -> float:
        p_words = set(prompt.lower().split())
        r_words = set(response.lower().split())
        if not p_words:
            return 1.0
        return min(1.0, len(p_words & r_words) / len(p_words) * 2)

    def compare(self, prompt: str, response_a: str, response_b: str, task_type: str = "general") -> Dict[str, Any]:
        eval_a = self.evaluate(prompt, response_a, task_type)
        eval_b = self.evaluate(prompt, response_b, task_type)
        winner = "A" if eval_a["overall_score"] > eval_b["overall_score"] else "B"
        return {
            "winner": winner,
            "score_a": eval_a["overall_score"],
            "score_b": eval_b["overall_score"],
            "details_a": eval_a,
            "details_b": eval_b,
        }


class CostMonitor:
    """Real-time cost tracking and alerting."""

    def __init__(self, budget_limit: float = 100.0):
        self.budget_limit = budget_limit
        self._usage: Dict[str, Dict[str, float]] = {}  # model -> {input_cost, output_cost, total}
        self._history: List[Dict[str, Any]] = []

    def record(self, model: str, input_tokens: int, output_tokens: int,
               cost_per_1k_input: float, cost_per_1k_output: float) -> None:
        in_cost = (input_tokens / 1000) * cost_per_1k_input
        out_cost = (output_tokens / 1000) * cost_per_1k_output
        total = in_cost + out_cost
        u = self._usage.setdefault(model, {"input_cost": 0.0, "output_cost": 0.0, "total": 0.0})
        u["input_cost"] += in_cost
        u["output_cost"] += out_cost
        u["total"] += total
        self._history.append({
            "timestamp": time.time(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": round(total, 4),
        })

    def get_usage(self, model: Optional[str] = None) -> Dict[str, Any]:
        if model:
            return self._usage.get(model, {"input_cost": 0.0, "output_cost": 0.0, "total": 0.0})
        total = sum(u["total"] for u in self._usage.values())
        return {"total_cost": round(total, 4), "models": dict(self._usage), "budget_limit": self.budget_limit}

    def is_over_budget(self) -> bool:
        total = sum(u["total"] for u in self._usage.values())
        return total > self.budget_limit

    def get_remaining_budget(self) -> float:
        total = sum(u["total"] for u in self._usage.values())
        return max(0.0, self.budget_limit - total)


class AlertManager:
    """Threshold-based alerting system."""

    def __init__(self):
        self._alerts: List[Alert] = []
        self._rules: List[Dict[str, Any]] = []

    def add_rule(self, name: str, metric_name: str, threshold: float,
                 comparator: str, severity: AlertSeverity, message: str) -> None:
        self._rules.append({
            "name": name,
            "metric_name": metric_name,
            "threshold": threshold,
            "comparator": comparator,  # >, <, >=, <=, ==
            "severity": severity,
            "message": message,
        })

    def check(self, metrics: Dict[str, float]) -> List[Alert]:
        triggered = []
        for rule in self._rules:
            value = metrics.get(rule["metric_name"], 0)
            cmp = rule["comparator"]
            triggered_alert = False
            if cmp == ">" and value > rule["threshold"]:
                triggered_alert = True
            elif cmp == "<" and value < rule["threshold"]:
                triggered_alert = True
            elif cmp == ">=" and value >= rule["threshold"]:
                triggered_alert = True
            elif cmp == "<=" and value <= rule["threshold"]:
                triggered_alert = True

            if triggered_alert:
                alert = Alert(
                    alert_id=str(uuid.uuid4())[:12],
                    name=rule["name"],
                    severity=rule["severity"],
                    message=rule["message"].format(value=value, threshold=rule["threshold"]),
                    metric_name=rule["metric_name"],
                    threshold=rule["threshold"],
                    actual_value=value,
                    timestamp=time.time(),
                )
                self._alerts.append(alert)
                triggered.append(alert)
        return triggered

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        alerts = [a for a in self._alerts if not a.acknowledged]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def acknowledge(self, alert_id: str) -> bool:
        for a in self._alerts:
            if a.alert_id == alert_id:
                a.acknowledged = True
                return True
        return False


class ObservabilityDashboard:
    """Aggregated observability view."""

    def __init__(self):
        self.metrics = MetricsCollector()
        self.tracer = Tracer()
        self.judge = LLMJudge()
        self.cost = CostMonitor()
        self.alerts = AlertManager()

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics.get_all_aggregates(),
            "traces": self.tracer.get_stats(),
            "cost": self.cost.get_usage(),
            "alerts": len(self.alerts.get_active_alerts()),
            "critical_alerts": len(self.alerts.get_active_alerts(AlertSeverity.CRITICAL)),
            "timestamp": time.time(),
        }

    def export_dashboard(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_snapshot(), f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("OBSERVABILITY & LLM-AS-A-JUDGE DEMO")
    print("=" * 70)

    # 1. Metrics
    print("\n[1] Metrics Collection")
    metrics = MetricsCollector()
    for i in range(10):
        metrics.record("request_latency", 0.1 + i * 0.05, MetricType.TIMER, {"endpoint": "/chat"}, "seconds")
        metrics.record("token_usage", 500 + i * 100, MetricType.COUNTER, {"model": "gpt-4"}, "tokens")
    print(f"  Latency avg: {metrics.get_aggregate('request_latency').get('avg', 0):.3f}s")
    print(f"  Token total: {metrics.get_aggregate('token_usage').get('sum', 0)} tokens")

    # 2. Timer context
    print("\n[2] Timer Context Manager")
    with metrics.timer("db_query", {"table": "users"}):
        time.sleep(0.01)
    print(f"  DB query time: {metrics.get_aggregate('db_query').get('last', 0):.3f}s")

    # 3. Tracing
    print("\n[3] Distributed Tracing")
    tracer = Tracer()
    span1 = tracer.start_span("api_request", metadata={"user_id": "u123"})
    span2 = tracer.start_span("llm_call", trace_id=span1.trace_id, parent_id=span1.span_id, metadata={"model": "gpt-4"})
    span3 = tracer.start_span("db_lookup", trace_id=span1.trace_id, parent_id=span1.span_id)
    time.sleep(0.01)
    tracer.end_span(span3.span_id)
    time.sleep(0.02)
    tracer.end_span(span2.span_id, "ok")
    tracer.end_span(span1.span_id, "ok")
    print(f"  Trace stats: {tracer.get_stats()}")
    tree = tracer.get_span_tree(span1.trace_id)
    print(f"  Tree root: {tree.get('name', 'N/A')} ({tree.get('duration', 0):.3f}s)")

    # 4. LLM-as-a-Judge
    print("\n[4] LLM-as-a-Judge")
    judge = LLMJudge()
    prompt = "What is the capital of France?"
    response = "The capital of France is Paris."
    eval_result = judge.evaluate(prompt, response)
    print(f"  Overall: {eval_result['overall_score']:.3f} ({eval_result['verdict']})")
    print(f"  Breakdown: {eval_result['scores']}")

    # Compare two responses
    response_b = "Paris is the capital."
    comparison = judge.compare(prompt, response, response_b)
    print(f"  Comparison: Winner={comparison['winner']} (A={comparison['score_a']:.3f}, B={comparison['score_b']:.3f})")

    # 5. Cost monitoring
    print("\n[5] Cost Monitoring")
    cost = CostMonitor(budget_limit=5.0)
    cost.record("gpt-4", 1000, 500, 0.03, 0.06)
    cost.record("gpt-4", 2000, 800, 0.03, 0.06)
    cost.record("claude-3.5", 1500, 600, 0.003, 0.015)
    print(f"  Total cost: ${cost.get_usage()['total_cost']:.4f}")
    print(f"  Budget remaining: ${cost.get_remaining_budget():.4f}")
    print(f"  Over budget? {cost.is_over_budget()}")

    # 6. Alerting
    print("\n[6] Alerting")
    alerts = AlertManager()
    alerts.add_rule("high_latency", "request_latency", 0.5, ">", AlertSeverity.WARNING, "Latency high: {value:.3f}s > {threshold}")
    alerts.add_rule("budget_exceeded", "total_cost", 10.0, ">=", AlertSeverity.CRITICAL, "Budget exceeded: ${value}")
    test_metrics = {"request_latency": 0.6, "total_cost": 12.0}
    triggered = alerts.check(test_metrics)
    print(f"  Triggered alerts: {len(triggered)}")
    for a in triggered:
        print(f"    [{a.severity.name}] {a.name}: {a.message}")
    print(f"  Active critical: {len(alerts.get_active_alerts(AlertSeverity.CRITICAL))}")

    # 7. Dashboard
    print("\n[7] Observability Dashboard")
    dashboard = ObservabilityDashboard()
    dashboard.metrics = metrics
    dashboard.tracer = tracer
    dashboard.cost = cost
    dashboard.alerts = alerts
    snapshot = dashboard.get_snapshot()
    print(f"  Snapshot keys: {list(snapshot.keys())}")
    print(f"  Critical alerts: {snapshot['critical_alerts']}")

    # 8. Export
    print("\n[8] Export")
    metrics.export("/tmp/metrics.json")
    dashboard.export_dashboard("/tmp/dashboard.json")
    print("  Exported to /tmp/metrics.json and /tmp/dashboard.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
