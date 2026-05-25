#!/usr/bin/env python3
"""
kernel/trace_propagator_native.py
===================================
Layer 0 — Distributed Trace Context Propagation

Propagates trace_id across all inter-layer messages (kernel bridge, P2P, event bus).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional


class TraceContext:
    """W3C Trace Context compatible propagator."""

    def __init__(self, trace_id: Optional[str] = None,
                 span_id: Optional[str] = None,
                 parent_id: Optional[str] = None) -> None:
        self.trace_id = trace_id or uuid.uuid4().hex
        self.span_id = span_id or uuid.uuid4().hex[:16]
        self.parent_id = parent_id

    def to_dict(self) -> Dict[str, str]:
        d = {"trace_id": self.trace_id, "span_id": self.span_id}
        if self.parent_id:
            d["parent_id"] = self.parent_id
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "TraceContext":
        return cls(d.get("trace_id"), d.get("span_id"), d.get("parent_id"))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, uuid.uuid4().hex[:16], self.span_id)


class TracePropagator:
    """Inject/extract trace context into messages."""

    @staticmethod
    def inject(headers: Dict[str, Any], ctx: TraceContext) -> None:
        headers["traceparent"] = f"00-{ctx.trace_id}-{ctx.span_id}-01"

    @staticmethod
    def extract(headers: Dict[str, Any]) -> Optional[TraceContext]:
        tp = headers.get("traceparent", "")
        parts = tp.split("-")
        if len(parts) >= 3:
            return TraceContext(parts[1], parts[2])
        return None
