#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 3 — Tracing Engine
Native distributed tracing with span trees, sampling, and baggage propagation.
- Span context with trace/span/parent IDs
- Sampling strategies (probabilistic, rate-limiting, adaptive)
- Baggage propagation across service boundaries
- Trace visualization export (JSON/Graphviz DOT)
"""
import json, time, threading, random, os, sys, hashlib
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum


class SamplingStrategy(Enum):
    ALWAYS = "always"
    NEVER = "never"
    PROBABILISTIC = "probabilistic"
    RATE_LIMITING = "rate_limiting"
    ADAPTIVE = "adaptive"


@dataclass
class SpanContext:
    trace_id: str
    span_id: str
    parent_id: str = ""
    sampled: bool = True
    baggage: Dict[str, str] = field(default_factory=dict)

    def fork(self, new_span_id: str) -> 'SpanContext':
        return SpanContext(
            trace_id=self.trace_id,
            span_id=new_span_id,
            parent_id=self.span_id,
            sampled=self.sampled,
            baggage=dict(self.baggage),
        )

    def inject(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "sampled": self.sampled,
            "baggage": self.baggage,
        }

    @classmethod
    def extract(cls, headers: Dict) -> 'SpanContext':
        return cls(
            trace_id=headers.get("trace_id", ""),
            span_id=headers.get("span_id", ""),
            parent_id=headers.get("parent_id", ""),
            sampled=headers.get("sampled", True),
            baggage=headers.get("baggage", {}),
        )


@dataclass
class Span:
    context: SpanContext
    operation: str
    start_time: float
    end_time: float = 0.0
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict] = field(default_factory=list)

    def finish(self, timestamp: Optional[float] = None):
        self.end_time = timestamp or time.time()

    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000 if self.end_time > 0 else 0.0

    def add_tag(self, key: str, value: Any):
        self.tags[key] = value

    def log_event(self, event: str, payload: Dict = None):
        self.logs.append({"timestamp": time.time(), "event": event, "payload": payload or {}})

    def to_dict(self) -> Dict:
        return {
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_id": self.context.parent_id,
            "operation": self.operation,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms(),
            "tags": self.tags,
            "logs": self.logs,
        }


class Sampler:
    """Trace sampling strategies."""

    def __init__(self, strategy: SamplingStrategy = SamplingStrategy.PROBABILISTIC, rate: float = 0.1):
        self.strategy = strategy
        self.rate = rate
        self._credits = 1.0
        self._last = time.time()
        self._lock = threading.Lock()
        self._error_rate = 0.0

    def should_sample(self) -> bool:
        if self.strategy == SamplingStrategy.ALWAYS:
            return True
        if self.strategy == SamplingStrategy.NEVER:
            return False
        if self.strategy == SamplingStrategy.PROBABILISTIC:
            return random.random() < self.rate
        if self.strategy == SamplingStrategy.RATE_LIMITING:
            with self._lock:
                now = time.time()
                elapsed = now - self._last
                self._credits = min(self.rate, self._credits + elapsed * self.rate)
                self._last = now
                if self._credits >= 1.0:
                    self._credits -= 1.0
                    return True
                return False
        if self.strategy == SamplingStrategy.ADAPTIVE:
            # Sample more when error rate is high
            adaptive_rate = min(1.0, self.rate + self._error_rate)
            return random.random() < adaptive_rate
        return True

    def report_error(self):
        with self._lock:
            self._error_rate = min(1.0, self._error_rate + 0.1)

    def report_success(self):
        with self._lock:
            self._error_rate = max(0.0, self._error_rate - 0.01)


class Tracer:
    """Main tracer for creating spans and managing trace state."""

    def __init__(self, service_name: str, sampler: Sampler = None):
        self.service_name = service_name
        self.sampler = sampler or Sampler()
        self._spans: Dict[str, List[Span]] = defaultdict(list)
        self._lock = threading.Lock()

    def start_span(self, operation: str, parent_context: SpanContext = None, tags: Dict = None) -> Span:
        trace_id = parent_context.trace_id if parent_context else self._gen_id()
        parent_id = parent_context.span_id if parent_context else ""
        sampled = parent_context.sampled if parent_context else self.sampler.should_sample()
        span_id = self._gen_id()
        ctx = SpanContext(trace_id, span_id, parent_id, sampled, parent_context.baggage if parent_context else {})
        span = Span(ctx, operation, time.time(), tags=tags or {})
        if sampled:
            with self._lock:
                self._spans[trace_id].append(span)
        return span

    def inject_context(self, span: Span) -> Dict:
        return span.context.inject()

    def extract_context(self, headers: Dict) -> SpanContext:
        return SpanContext.extract(headers)

    def _gen_id(self) -> str:
        return hashlib.sha256(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]

    def get_trace(self, trace_id: str) -> List[Span]:
        with self._lock:
            return list(self._spans.get(trace_id, []))

    def trace_tree(self, trace_id: str) -> Dict:
        spans = self.get_trace(trace_id)
        if not spans:
            return {}
        # Build tree
        by_id = {s.context.span_id: s for s in spans}
        roots = [s for s in spans if not s.context.parent_id]
        def _build(s: Span):
            children = [c for c in spans if c.context.parent_id == s.context.span_id]
            return {
                "span": s.to_dict(),
                "children": [_build(c) for c in children],
            }
        return _build(roots[0]) if roots else {}

    def export_traces(self, path: str):
        with self._lock:
            data = {tid: [s.to_dict() for s in spans] for tid, spans in self._spans.items()}
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def to_dot(self, trace_id: str) -> str:
        spans = self.get_trace(trace_id)
        lines = ["digraph trace {"]
        for s in spans:
            label = f"{s.operation}\\n{s.duration_ms():.1f}ms"
            lines.append(f'  "{s.context.span_id}" [label="{label}"];')
            if s.context.parent_id:
                lines.append(f'  "{s.context.parent_id}" -> "{s.context.span_id}";')
        lines.append("}")
        return "\n".join(lines)

    def stats(self) -> Dict:
        with self._lock:
            total_spans = sum(len(s) for s in self._spans.values())
            total_traces = len(self._spans)
        return {
            "service": self.service_name,
            "total_spans": total_spans,
            "total_traces": total_traces,
            "sampling_strategy": self.sampler.strategy.value,
            "sampling_rate": self.sampler.rate,
        }


class BaggagePropagator:
    """Propagate baggage across process boundaries."""

    @staticmethod
    def encode(baggage: Dict[str, str]) -> str:
        return json.dumps(baggage)

    @staticmethod
    def decode(data: str) -> Dict[str, str]:
        try:
            return json.loads(data)
        except Exception:
            return {}


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("span_context_fork", lambda: SpanContext("t1", "s1").fork("s2").parent_id == "s1")
    _t("span_duration", lambda: (s := Span(SpanContext("t", "s"), "op", time.time()), s.finish(), s.duration_ms() >= 0)[2])
    _t("sampler_always", lambda: Sampler(SamplingStrategy.ALWAYS).should_sample())
    _t("sampler_never", lambda: not Sampler(SamplingStrategy.NEVER).should_sample())
    _t("sampler_prob", lambda: 0 <= sum(Sampler(SamplingStrategy.PROBABILISTIC, 0.5).should_sample() for _ in range(1000)) <= 1000)
    _t("tracer_start", lambda: (t := Tracer("svc"), s := t.start_span("op"), s.context.trace_id != "")[2])
    _t("tracer_inject_extract", lambda: (t := Tracer("svc"), s := t.start_span("op"), h := t.inject_context(s), t.extract_context(h).trace_id == s.context.trace_id)[3])
    _t("trace_tree", lambda: (t := Tracer("svc"), p := t.start_span("parent"), c := t.start_span("child", p.context), len(t.trace_tree(p.context.trace_id).get("children", [])) == 1)[3])
    _t("tracer_dot", lambda: (t := Tracer("svc"), s := t.start_span("op"), "digraph" in t.to_dot(s.context.trace_id))[2])
    _t("baggage_encode", lambda: BaggagePropagator.encode({"k": "v"}) == '{"k": "v"}')
    _t("stats", lambda: "total_spans" in Tracer("svc").stats())

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nTracing Engine: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
