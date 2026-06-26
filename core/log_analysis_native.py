#!/usr/bin/env python3
"""Log Analysis Engine for MAGNATRIX-OS — AI-powered log anomaly detection."""
from __future__ import annotations
import json, re, statistics, time
from typing import Any, Dict, List

class LogAnalysisEngine:
    def __init__(self) -> None:
        self._patterns: Dict[str, int] = {}
        self._anomalies: List[Dict[str, Any]] = []

    def ingest(self, log_line: str) -> None:
        # Extract pattern (remove variable parts)
        pattern = re.sub(r'\d+', 'NUM', log_line)
        pattern = re.sub(r'[a-f0-9]{8,}', 'HASH', pattern)
        self._patterns[pattern] = self._patterns.get(pattern, 0) + 1

    def detect_anomalies(self, threshold: int = 3) -> List[Dict[str, Any]]:
        if not self._patterns:
            return []
        counts = list(self._patterns.values())
        mean = statistics.mean(counts)
        stdev = statistics.stdev(counts) if len(counts) > 1 else 0
        anomalies = []
        for pattern, count in self._patterns.items():
            if stdev > 0 and abs(count - mean) > threshold * stdev:
                anomalies.append({"pattern": pattern, "count": count, "expected": mean})
        return anomalies

    def stats(self) -> Dict[str, Any]:
        return {"patterns": len(self._patterns), "anomalies": len(self._anomalies)}
