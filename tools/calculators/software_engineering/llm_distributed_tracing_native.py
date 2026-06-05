"""Distributed Tracing — span, trace, context propagation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto
import time
import uuid

class SpanStatus(Enum):
    OK = auto()
    ERROR = auto()
    PENDING = auto()

@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_id: Optional[str] = None
    operation: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    status: SpanStatus = SpanStatus.PENDING
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict] = field(default_factory=list)

    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

    def finish(self, status: SpanStatus = SpanStatus.OK):
        self.end_time = time.time()
        self.status = status

class Tracer:
    def __init__(self, service_name: str = "unknown"):
        self.service_name = service_name
        self.active_spans: Dict[str, Span] = {}
        self.finished_spans: List[Span] = []

    def start_span(self, operation: str, trace_id: Optional[str] = None, parent_id: Optional[str] = None) -> Span:
        span_id = str(uuid.uuid4())[:8]
        trace_id = trace_id or str(uuid.uuid4())[:8]
        span = Span(span_id, trace_id, parent_id, operation, time.time())
        self.active_spans[span_id] = span
        return span

    def finish_span(self, span_id: str, status: SpanStatus = SpanStatus.OK):
        span = self.active_spans.pop(span_id, None)
        if span:
            span.finish(status)
            self.finished_spans.append(span)

    def log(self, span_id: str, event: str, payload: Dict = None):
        span = self.active_spans.get(span_id)
        if span:
            span.logs.append({"time": time.time(), "event": event, "payload": payload or {}})

    def tag(self, span_id: str, key: str, value: Any):
        span = self.active_spans.get(span_id)
        if span:
            span.tags[key] = value

    def get_trace(self, trace_id: str) -> List[Span]:
        return [s for s in self.finished_spans if s.trace_id == trace_id]

    def stats(self) -> Dict:
        return {"service": self.service_name, "active": len(self.active_spans), "finished": len(self.finished_spans), "avg_duration_ms": sum(s.duration_ms() for s in self.finished_spans) / len(self.finished_spans) if self.finished_spans else 0}

def run():
    tracer = Tracer("api-gateway")
    s1 = tracer.start_span("handle_request")
    tracer.tag(s1.span_id, "user", "alice")
    s2 = tracer.start_span("query_db", trace_id=s1.trace_id, parent_id=s1.span_id)
    time.sleep(0.01)
    tracer.finish_span(s2.span_id)
    tracer.finish_span(s1.span_id)
    print(tracer.get_trace(s1.trace_id))
    print(tracer.stats())

if __name__ == "__main__":
    run()
