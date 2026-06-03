"""LLM Tracer — Native Python (stdlib only)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class SpanStatus(Enum):
    OK = auto()
    ERROR = auto()
    CANCELLED = auto()

@dataclass
class Span:
    id: str
    name: str
    parent_id: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0
    status: SpanStatus = SpanStatus.OK
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time > 0 else 0.0

class Tracer:
    def __init__(self) -> None:
        self._spans: Dict[str, Span] = {}
        self._active: List[str] = []
        self._traces: Dict[str, List[str]] = {}

    def start_span(self, trace_id: str, name: str, parent_id: Optional[str] = None) -> str:
        span_id = trace_id + "_" + name + "_" + str(len(self._spans))
        span = Span(id=span_id, name=name, parent_id=parent_id or (self._active[-1] if self._active else None), start_time=time.time())
        self._spans[span_id] = span
        if trace_id not in self._traces:
            self._traces[trace_id] = []
        self._traces[trace_id].append(span_id)
        self._active.append(span_id)
        return span_id

    def end_span(self, span_id: str, status: SpanStatus = SpanStatus.OK) -> None:
        span = self._spans.get(span_id)
        if span:
            span.end_time = time.time()
            span.status = status
        if span_id in self._active:
            self._active.remove(span_id)

    def get_trace(self, trace_id: str) -> List[Span]:
        span_ids = self._traces.get(trace_id, [])
        return [self._spans[sid] for sid in span_ids if sid in self._spans]

    def get_stats(self, trace_id: str) -> Dict[str, Any]:
        spans = self.get_trace(trace_id)
        total = sum(s.duration() for s in spans)
        return {"spans": len(spans), "total_duration": total, "avg_duration": total / len(spans) if spans else 0.0, "errors": sum(1 for s in spans if s.status == SpanStatus.ERROR)}

def run() -> None:
    print("Tracer test")
    e = Tracer()
    s1 = e.start_span("trace_1", "request")
    s2 = e.start_span("trace_1", "validation", s1)
    s3 = e.start_span("trace_1", "processing", s2)
    e.end_span(s3)
    e.end_span(s2)
    e.end_span(s1)
    spans = e.get_trace("trace_1")
    for s in spans:
        print("  " + s.name + ": " + str(s.duration()) + "s")
    print("  Stats: " + str(e.get_stats("trace_1")))
    print("Tracer test complete.")

if __name__ == "__main__":
    run()
