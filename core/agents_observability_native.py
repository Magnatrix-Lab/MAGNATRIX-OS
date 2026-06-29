"""Agents Observability - Monitoring, tracing, and logging for ADK agents."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TraceSpan:
    span_id: str
    trace_id: str
    name: str
    start_time: float
    end_time: float = 0.0
    attributes: Dict[str, str] = field(default_factory=dict)
    status: str = "ok"  # ok, error, cancelled

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000.0

    def to_dict(self) -> Dict:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "attributes": self.attributes,
            "status": self.status,
        }


@dataclass
class LogEntry:
    log_id: str
    timestamp: float
    level: str = "INFO"
    message: str = ""
    source: str = "agent"
    agent_name: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "agent_name": self.agent_name,
            "metadata": self.metadata,
        }


@dataclass
class MetricPoint:
    metric_name: str
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "metric_name": self.metric_name,
            "timestamp": self.timestamp,
            "value": self.value,
            "labels": self.labels,
        }


class AgentsObservability:
    """Observability — Cloud Trace, logging, and metrics collection."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "agents_observability"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.spans: Dict[str, TraceSpan] = {}
        self.logs: List[LogEntry] = []
        self.metrics: List[MetricPoint] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for s in data.get("spans", []):
                    self.spans[s["span_id"]] = TraceSpan(**s)
                for l in data.get("logs", []):
                    self.logs.append(LogEntry(**l))
                for m in data.get("metrics", []):
                    self.metrics.append(MetricPoint(**m))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "spans": [s.to_dict() for s in self.spans.values()],
            "logs": [l.to_dict() for l in self.logs[-5000:]],  # Keep last 5000
            "metrics": [m.to_dict() for m in self.metrics[-5000:]],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def start_trace(self, trace_name: str, agent_name: str = "", trace_id: str = "") -> str:
        """Start a new distributed trace."""
        if not trace_id:
            trace_id = hashlib.md5(f"{trace_name}{time.time()}".encode()).hexdigest()[:16]
        span_id = f"span_{trace_id}_root"
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            name=trace_name,
            start_time=time.time(),
            attributes={"agent": agent_name},
        )
        self.spans[span_id] = span
        self._save_state()
        return trace_id

    def end_trace(self, trace_id: str) -> Optional[TraceSpan]:
        """End a trace."""
        root_span = None
        for span in self.spans.values():
            if span.trace_id == trace_id and span.span_id.endswith("_root"):
                span.end_time = time.time()
                root_span = span
                break
        self._save_state()
        return root_span

    def add_span(self, trace_id: str, name: str, attributes: Optional[Dict[str, str]] = None) -> TraceSpan:
        """Add a child span to a trace."""
        span_id = f"span_{trace_id}_{hashlib.md5(f'{name}{time.time()}'.encode()).hexdigest()[:8]}"
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            name=name,
            start_time=time.time(),
            attributes=attributes or {},
        )
        self.spans[span_id] = span
        self._save_state()
        return span

    def end_span(self, span_id: str, status: str = "ok") -> TraceSpan:
        """End a span."""
        if span_id not in self.spans:
            raise ValueError(f"Span {span_id} not found")
        span = self.spans[span_id]
        span.end_time = time.time()
        span.status = status
        self._save_state()
        return span

    def log(self, message: str, level: str = "INFO", agent_name: str = "", source: str = "agent", metadata: Optional[Dict[str, str]] = None) -> LogEntry:
        """Emit a structured log entry."""
        entry = LogEntry(
            log_id=f"log_{int(time.time() * 1000)}_{hashlib.md5(message.encode()).hexdigest()[:6]}",
            timestamp=time.time(),
            level=level,
            message=message,
            source=source,
            agent_name=agent_name,
            metadata=metadata or {},
        )
        self.logs.append(entry)
        self._save_state()
        return entry

    def record_metric(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> MetricPoint:
        """Record a metric data point."""
        point = MetricPoint(
            metric_name=metric_name,
            timestamp=time.time(),
            value=value,
            labels=labels or {},
        )
        self.metrics.append(point)
        self._save_state()
        return point

    def get_trace_summary(self, trace_id: str) -> Dict:
        """Get summary of a trace."""
        trace_spans = [s for s in self.spans.values() if s.trace_id == trace_id]
        if not trace_spans:
            return {"trace_id": trace_id, "found": False}
        total_ms = sum(s.duration_ms for s in trace_spans if s.end_time > 0)
        errors = sum(1 for s in trace_spans if s.status == "error")
        return {
            "trace_id": trace_id,
            "span_count": len(trace_spans),
            "total_duration_ms": round(total_ms, 2),
            "error_count": errors,
            "spans": [s.to_dict() for s in trace_spans],
        }

    def get_logs(self, agent_name: str = "", level: str = "", limit: int = 100) -> List[Dict]:
        """Query logs with filters."""
        results = self.logs
        if agent_name:
            results = [l for l in results if l.agent_name == agent_name]
        if level:
            results = [l for l in results if l.level == level]
        return [l.to_dict() for l in results[-limit:]]

    def get_metric_series(self, metric_name: str, agent_name: str = "") -> List[Dict]:
        """Get time series for a metric."""
        points = [m for m in self.metrics if m.metric_name == metric_name]
        if agent_name:
            points = [m for m in points if m.labels.get("agent") == agent_name]
        return [p.to_dict() for p in points]

    def get_stats(self) -> Dict:
        return {
            "spans_total": len(self.spans),
            "logs_total": len(self.logs),
            "metrics_total": len(self.metrics),
            "error_count": sum(1 for s in self.spans.values() if s.status == "error"),
        }

    def to_dict(self) -> Dict:
        return {
            "spans": [s.to_dict() for s in self.spans.values()],
            "logs": [l.to_dict() for l in self.logs[-100:]],
            "metrics": [m.to_dict() for m in self.metrics[-100:]],
            "stats": self.get_stats(),
        }


__all__ = ["AgentsObservability", "TraceSpan", "LogEntry", "MetricPoint"]
