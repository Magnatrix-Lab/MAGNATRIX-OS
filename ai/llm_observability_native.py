"""
llm_observability_native.py
MAGNATRIX-OS Observability Engine
Native Python, stdlib only.
Provides distributed tracing, span collection, correlation IDs, latency tracking,
and trace export for end-to-end request visibility across MAGNATRIX-OS services.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class SpanStatus(Enum):
    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.OK
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id, "trace_id": self.trace_id,
            "parent_id": self.parent_id, "name": self.name,
            "start_time": self.start_time, "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 3),
            "status": self.status.value, "attributes": self.attributes,
            "events": self.events, "links": self.links,
        }

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({"name": name, "timestamp": time.time(), "attributes": attributes or {}})

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def finish(self, status: Optional[SpanStatus] = None) -> None:
        self.end_time = time.time()
        if status:
            self.status = status


@dataclass
class Trace:
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    root_span_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "root_span_id": self.root_span_id,
            "span_count": len(self.spans),
            "total_duration_ms": round(self.total_duration_ms, 3),
            "spans": [s.to_dict() for s in self.spans],
        }

    @property
    def total_duration_ms(self) -> float:
        if not self.spans:
            return 0.0
        starts = [s.start_time for s in self.spans]
        ends = [s.end_time or time.time() for s in self.spans]
        return (max(ends) - min(starts)) * 1000

    def get_span(self, span_id: str) -> Optional[Span]:
        for s in self.spans:
            if s.span_id == span_id:
                return s
        return None


class ObservabilityEngine:
    """
    Distributed tracing and observability engine.
    """

    def __init__(self) -> None:
        self._traces: Dict[str, Trace] = {}
        self._active_spans: Dict[str, Span] = {}
        self._lock = threading.Lock()
        self._exporters: List[Callable[[Trace], None]] = []
        self._sampler = lambda: True  # Always sample
        self._span_counter = 0

    def set_sampler(self, sampler: Callable[[], bool]) -> None:
        self._sampler = sampler

    def start_trace(self, name: str, trace_id: Optional[str] = None,
                    attributes: Optional[Dict[str, Any]] = None) -> Span:
        tid = trace_id or self._generate_id()
        span_id = self._generate_id()
        span = Span(
            span_id=span_id, trace_id=tid, parent_id=None,
            name=name, start_time=time.time(), attributes=attributes or {}
        )
        trace = Trace(trace_id=tid, spans=[span], root_span_id=span_id)
        with self._lock:
            self._traces[tid] = trace
            self._active_spans[span_id] = span
        return span

    def start_span(self, trace_id: str, name: str, parent_id: Optional[str] = None,
                   attributes: Optional[Dict[str, Any]] = None) -> Span:
        span_id = self._generate_id()
        span = Span(
            span_id=span_id, trace_id=trace_id, parent_id=parent_id,
            name=name, start_time=time.time(), attributes=attributes or {}
        )
        with self._lock:
            if trace_id in self._traces:
                self._traces[trace_id].spans.append(span)
            else:
                self._traces[trace_id] = Trace(trace_id=trace_id, spans=[span])
            self._active_spans[span_id] = span
        return span

    def finish_span(self, span_id: str, status: Optional[SpanStatus] = None) -> Optional[Span]:
        with self._lock:
            span = self._active_spans.pop(span_id, None)
        if span:
            span.finish(status)
        return span

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        return self._traces.get(trace_id)

    def get_active_spans(self) -> List[Span]:
        return list(self._active_spans.values())

    def add_exporter(self, exporter: Callable[[Trace], None]) -> None:
        self._exporters.append(exporter)

    def export_trace(self, trace_id: str) -> None:
        trace = self._traces.get(trace_id)
        if trace:
            for exporter in self._exporters:
                try:
                    exporter(trace)
                except Exception:
                    pass

    def get_traces(self, limit: int = 100) -> List[Trace]:
        traces = list(self._traces.values())
        traces.sort(key=lambda t: min((s.start_time for s in t.spans), default=0), reverse=True)
        return traces[:limit]

    def get_trace_stats(self, trace_id: str) -> Dict[str, Any]:
        trace = self._traces.get(trace_id)
        if not trace:
            return {}
        spans = trace.spans
        durations = [s.duration_ms for s in spans if s.end_time is not None]
        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "active_spans": sum(1 for s in spans if s.end_time is None),
            "total_duration_ms": round(trace.total_duration_ms, 3),
            "avg_span_duration_ms": round(sum(durations) / len(durations), 3) if durations else 0,
            "max_span_duration_ms": round(max(durations), 3) if durations else 0,
            "error_count": sum(1 for s in spans if s.status == SpanStatus.ERROR),
        }

    def clear(self, trace_id: Optional[str] = None) -> None:
        if trace_id:
            self._traces.pop(trace_id, None)
            self._active_spans = {k: v for k, v in self._active_spans.items() if v.trace_id != trace_id}
        else:
            self._traces.clear()
            self._active_spans.clear()

    def _generate_id(self) -> str:
        self._span_counter += 1
        return f"{uuid.uuid4().hex[:16]}_{self._span_counter}"

    def export_all(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self._traces.values()], f, indent=2, default=str)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Observability Engine")
    print("=" * 60)

    engine = ObservabilityEngine()

    # Add exporter
    def console_exporter(trace: Trace) -> None:
        print(f"  [Export] Trace {trace.trace_id}: {len(trace.spans)} spans")

    engine.add_exporter(console_exporter)

    print("\n--- Start trace ---")
    root = engine.start_trace("llm_request", attributes={"user_id": "U123", "model": "gpt-4o"})
    print(f"  Trace: {root.trace_id}, Root span: {root.span_id}")

    # Simulate child spans
    span1 = engine.start_span(root.trace_id, "tokenize", parent_id=root.span_id, attributes={"tokens_in": 50})
    time.sleep(0.01)
    engine.finish_span(span1.span_id)

    span2 = engine.start_span(root.trace_id, "inference", parent_id=root.span_id, attributes={"model": "gpt-4o"})
    time.sleep(0.02)
    engine.finish_span(span2.span_id, SpanStatus.OK)

    span3 = engine.start_span(root.trace_id, "postprocess", parent_id=root.span_id)
    engine.finish_span(span3.span_id)

    root.finish()

    print("\n--- Trace stats ---")
    stats = engine.get_trace_stats(root.trace_id)
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n--- Export trace ---")
    engine.export_trace(root.trace_id)

    print("\n--- All traces ---")
    for trace in engine.get_traces():
        print(f"  {trace.trace_id}: {trace.span_count} spans, {trace.total_duration_ms:.2f}ms")

    print("\nObservability test complete.")


if __name__ == "__main__":
    run()
