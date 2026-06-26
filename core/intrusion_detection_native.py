#!/usr/bin/env python3
"""Intrusion Detection System for MAGNATRIX-OS — Anomaly-based IDS."""
from __future__ import annotations
import json, re, time, threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class SecurityEvent:
    timestamp: float
    source_ip: str
    event_type: str
    severity: str
    details: str

class IntrusionDetectionSystem:
    def __init__(self, alert_threshold: int = 5, window_seconds: int = 60) -> None:
        self._events: deque = deque(maxlen=10000)
        self._alert_threshold = alert_threshold
        self._window_seconds = window_seconds
        self._blocked_ips: set = set()
        self._lock = threading.Lock()

    def log_event(self, source_ip: str, event_type: str, severity: str = "low", details: str = "") -> None:
        event = SecurityEvent(timestamp=time.time(), source_ip=source_ip, event_type=event_type, severity=severity, details=details)
        self._events.append(event)
        self._evaluate(source_ip)

    def _evaluate(self, ip: str) -> None:
        with self._lock:
            now = time.time()
            recent = [e for e in self._events if e.source_ip == ip and now - e.timestamp < self._window_seconds]
            high_sev = sum(1 for e in recent if e.severity in ("high", "critical"))
            if len(recent) > self._alert_threshold or high_sev > 2:
                self._blocked_ips.add(ip)

    def is_blocked(self, ip: str) -> bool:
        return ip in self._blocked_ips

    def unblock(self, ip: str) -> None:
        self._blocked_ips.discard(ip)

    def stats(self) -> Dict[str, Any]:
        return {"total_events": len(self._events), "blocked_ips": len(self._blocked_ips), "events": len(self._events)}
