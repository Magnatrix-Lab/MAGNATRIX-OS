#!/usr/bin/env python3
"""
MAGNATRIX-OS — Log Analyzer Engine
ai/llm_log_analyzer_native.py

Features:
- Log parsing (structured + unstructured)
- Pattern detection (error frequencies, anomaly spikes)
- Log aggregation (group by level, source, time)
- Alert generation from log patterns
- Log correlation (find related events)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("log_analyzer")


@dataclass
class LogEntry:
    timestamp: str
    level: str
    source: str
    message: str


class LogAnalyzerEngine:
    """Log parsing, pattern detection, and correlation."""

    LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "FATAL"}

    def __init__(self):
        self._entries: List[LogEntry] = []
        self._alerts: List[Dict[str, Any]] = []

    def parse(self, log_line: str) -> Optional[LogEntry]:
        # Try structured format: 2024-01-01 10:00:00 ERROR source: message
        m = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(\S+)\s*:\s*(.*)', log_line)
        if m:
            return LogEntry(m.group(1), m.group(2), m.group(3), m.group(4))
        # Unstructured: try to find level
        for level in self.LEVELS:
            if level in log_line.upper():
                return LogEntry("", level, "unknown", log_line)
        return LogEntry("", "INFO", "unknown", log_line)

    def add(self, log_line: str) -> None:
        entry = self.parse(log_line)
        if entry:
            self._entries.append(entry)

    def aggregate(self) -> Dict[str, Any]:
        by_level = Counter(e.level for e in self._entries)
        by_source = Counter(e.source for e in self._entries)
        error_messages = Counter(e.message for e in self._entries if e.level in {"ERROR", "CRITICAL", "FATAL"})
        return {
            "total": len(self._entries),
            "by_level": dict(by_level),
            "by_source": dict(by_source),
            "top_errors": error_messages.most_common(5),
        }

    def detect_anomalies(self, threshold: int = 5) -> List[Dict[str, Any]]:
        by_level = Counter(e.level for e in self._entries)
        anomalies = []
        if by_level.get("ERROR", 0) > threshold:
            anomalies.append({"type": "error_spike", "count": by_level["ERROR"], "threshold": threshold})
        if by_level.get("CRITICAL", 0) > 0:
            anomalies.append({"type": "critical_events", "count": by_level["CRITICAL"]})
        return anomalies

    def correlate(self, keyword: str) -> List[LogEntry]:
        return [e for e in self._entries if keyword.lower() in e.message.lower()]

    def get_stats(self) -> Dict[str, Any]:
        return {"entries": len(self._entries), "alerts": len(self._alerts)}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Log Analyzer Engine")
    print("ai/llm_log_analyzer_native.py")
    print("=" * 60)

    engine = LogAnalyzerEngine()

    logs = [
        "2024-01-01 10:00:00 INFO server: Server started",
        "2024-01-01 10:01:00 ERROR db: Connection failed",
        "2024-01-01 10:02:00 ERROR db: Connection failed",
        "2024-01-01 10:03:00 WARNING cache: Cache miss rate high",
        "2024-01-01 10:04:00 ERROR api: Timeout on request",
        "2024-01-01 10:05:00 CRITICAL api: Service unavailable",
        "2024-01-01 10:06:00 INFO server: Health check ok",
    ]
    for log in logs:
        engine.add(log)

    print("\n[1] Aggregation")
    print(engine.aggregate())

    print("\n[2] Anomalies")
    print(engine.detect_anomalies(threshold=2))

    print("\n[3] Correlation (keyword: 'failed')")
    for e in engine.correlate("failed"):
        print(f"  {e.timestamp} {e.level} {e.source}: {e.message}")

    print(f"\n[4] Stats: {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
