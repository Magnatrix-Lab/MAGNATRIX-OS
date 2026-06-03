"""
llm_anomaly_detector_native.py
MAGNATRIX-OS Anomaly Detection Engine
Native Python, stdlib only.
Provides statistical anomaly detection with z-score, IQR, moving average deviation,
and rule-based threshold detection for LLM metrics and behavior monitoring.
"""

from __future__ import annotations

import json
import math
import statistics
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class AnomalyMethod(Enum):
    Z_SCORE = "z_score"
    IQR = "iqr"
    MOVING_AVERAGE = "moving_average"
    THRESHOLD = "threshold"
    PERCENT_CHANGE = "percent_change"


class AnomalySeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AnomalyEvent:
    timestamp: float
    method: AnomalyMethod
    severity: AnomalySeverity
    value: float
    expected: float
    deviation: float
    metric_name: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp, "method": self.method.value,
            "severity": self.severity.value, "value": self.value,
            "expected": self.expected, "deviation": self.deviation,
            "metric_name": self.metric_name, "message": self.message,
            "metadata": self.metadata,
        }


class AnomalyDetectorEngine:
    """
    Multi-method anomaly detection engine for time-series and point data.
    """

    def __init__(self) -> None:
        self._history: Dict[str, List[float]] = {}  # metric_name -> values
        self._detectors: Dict[str, Dict[str, Any]] = {}  # metric_name -> config
        self._alerts: List[AnomalyEvent] = []
        self._handlers: List[Callable[[AnomalyEvent], None]] = []
        self._max_history: int = 1000

    def register_metric(self, name: str, method: AnomalyMethod, params: Dict[str, Any] = None) -> None:
        self._detectors[name] = {"method": method, "params": params or {}}
        if name not in self._history:
            self._history[name] = []

    def observe(self, metric_name: str, value: float, metadata: Optional[Dict[str, Any]] = None) -> Optional[AnomalyEvent]:
        if metric_name not in self._history:
            self._history[metric_name] = []
        self._history[metric_name].append(value)
        if len(self._history[metric_name]) > self._max_history:
            self._history[metric_name] = self._history[metric_name][-self._max_history:]

        detector = self._detectors.get(metric_name)
        if not detector:
            return None

        event = self._detect(metric_name, value, detector["method"], detector["params"], metadata)
        if event:
            self._alerts.append(event)
            for handler in self._handlers:
                try:
                    handler(event)
                except Exception:
                    pass
        return event

    def _detect(self, name: str, value: float, method: AnomalyMethod, params: Dict[str, Any],
                metadata: Optional[Dict[str, Any]]) -> Optional[AnomalyEvent]:
        history = self._history.get(name, [])

        if method == AnomalyMethod.Z_SCORE:
            if len(history) < 2:
                return None
            mean = statistics.mean(history)
            stdev = statistics.stdev(history) if len(history) > 1 else 0
            if stdev == 0:
                return None
            z = (value - mean) / stdev
            threshold = params.get("threshold", 3.0)
            if abs(z) > threshold:
                severity = AnomalySeverity.CRITICAL if abs(z) > threshold * 1.5 else AnomalySeverity.WARNING
                return AnomalyEvent(
                    timestamp=time.time(), method=method, severity=severity,
                    value=value, expected=mean, deviation=z,
                    metric_name=name, message=f"Z-score anomaly: z={z:.2f}", metadata=metadata or {}
                )

        elif method == AnomalyMethod.IQR:
            if len(history) < 4:
                return None
            q1 = statistics.quantiles(history, n=4)[0]
            q3 = statistics.quantiles(history, n=4)[2]
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            if value < lower or value > upper:
                return AnomalyEvent(
                    timestamp=time.time(), method=method, severity=AnomalySeverity.WARNING,
                    value=value, expected=(lower + upper) / 2, deviation=value - (lower + upper) / 2,
                    metric_name=name, message=f"IQR outlier: value outside [{lower:.2f}, {upper:.2f}]",
                    metadata=metadata or {}
                )

        elif method == AnomalyMethod.MOVING_AVERAGE:
            window = params.get("window", 10)
            if len(history) < window + 1:
                return None
            recent = history[-window:]
            ma = statistics.mean(recent)
            threshold = params.get("threshold", 2.0)
            deviation = abs(value - ma) / ma if ma != 0 else 0
            if deviation > threshold:
                return AnomalyEvent(
                    timestamp=time.time(), method=method, severity=AnomalySeverity.WARNING,
                    value=value, expected=ma, deviation=deviation,
                    metric_name=name, message=f"Moving avg deviation: {deviation:.2%}",
                    metadata=metadata or {}
                )

        elif method == AnomalyMethod.THRESHOLD:
            min_val = params.get("min", float("-inf"))
            max_val = params.get("max", float("inf"))
            if value < min_val or value > max_val:
                severity = AnomalySeverity.CRITICAL if value > max_val * 1.5 or value < min_val * 0.5 else AnomalySeverity.WARNING
                return AnomalyEvent(
                    timestamp=time.time(), method=method, severity=severity,
                    value=value, expected=(min_val + max_val) / 2, deviation=value - (min_val + max_val) / 2,
                    metric_name=name, message=f"Threshold breach: {value} not in [{min_val}, {max_val}]",
                    metadata=metadata or {}
                )

        elif method == AnomalyMethod.PERCENT_CHANGE:
            if len(history) < 2:
                return None
            prev = history[-2]
            if prev == 0:
                return None
            change = abs((value - prev) / prev)
            threshold = params.get("threshold", 0.5)
            if change > threshold:
                return AnomalyEvent(
                    timestamp=time.time(), method=method, severity=AnomalySeverity.WARNING,
                    value=value, expected=prev, deviation=change,
                    metric_name=name, message=f"Percent change anomaly: {change:.2%}",
                    metadata=metadata or {}
                )

        return None

    def add_handler(self, handler: Callable[[AnomalyEvent], None]) -> None:
        self._handlers.append(handler)

    def get_alerts(self, metric_name: Optional[str] = None, severity: Optional[AnomalySeverity] = None) -> List[AnomalyEvent]:
        alerts = self._alerts
        if metric_name:
            alerts = [a for a in alerts if a.metric_name == metric_name]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def get_stats(self, metric_name: str) -> Dict[str, Any]:
        history = self._history.get(metric_name, [])
        if not history:
            return {}
        return {
            "count": len(history),
            "mean": statistics.mean(history),
            "stdev": statistics.stdev(history) if len(history) > 1 else 0,
            "min": min(history),
            "max": max(history),
            "alerts": len([a for a in self._alerts if a.metric_name == metric_name]),
        }

    def export_alerts(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([a.to_dict() for a in self._alerts], f, indent=2, default=str)

    def clear(self, metric_name: Optional[str] = None) -> None:
        if metric_name:
            self._history.pop(metric_name, None)
            self._alerts = [a for a in self._alerts if a.metric_name != metric_name]
        else:
            self._history.clear()
            self._alerts.clear()


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Anomaly Detection Engine")
    print("=" * 60)

    engine = AnomalyDetectorEngine()

    # Register detectors
    engine.register_metric("latency_ms", AnomalyMethod.Z_SCORE, {"threshold": 2.0})
    engine.register_metric("error_rate", AnomalyMethod.THRESHOLD, {"max": 0.05})
    engine.register_metric("throughput", AnomalyMethod.PERCENT_CHANGE, {"threshold": 0.3})
    engine.register_metric("memory_pct", AnomalyMethod.IQR)

    # Handler
    def on_alert(event: AnomalyEvent) -> None:
        print(f"  [ALERT] {event.severity.value.upper()}: {event.message}")

    engine.add_handler(on_alert)

    print("\n--- Simulating latency metrics ---")
    for i in range(20):
        # Normal latency around 100ms, occasional spike
        val = 100 + random.randint(-10, 10) if i != 15 else 500
        event = engine.observe("latency_ms", val)
        if event:
            print(f"  Value {val} -> ANOMALY")

    print("\n--- Simulating error rate ---")
    for val in [0.01, 0.02, 0.03, 0.01, 0.08, 0.01]:
        event = engine.observe("error_rate", val)
        if event:
            print(f"  Value {val} -> ANOMALY")

    print("\n--- Stats ---")
    for metric in ["latency_ms", "error_rate"]:
        stats = engine.get_stats(metric)
        print(f"  {metric}: {stats}")

    print(f"\n--- Total alerts: {len(engine.get_alerts())} ---")
    for sev in AnomalySeverity:
        count = len(engine.get_alerts(severity=sev))
        print(f"  {sev.value}: {count}")

    print("\nAnomaly Detector test complete.")


if __name__ == "__main__":
    run()
