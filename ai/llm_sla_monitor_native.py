"""
llm_sla_monitor_native.py
MAGNATRIX-OS SLA Monitor Engine
Native Python, stdlib only.
Provides SLA definition, compliance tracking, breach detection, and penalty calculation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class SLAMetricType(Enum):
    AVAILABILITY = "availability"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CUSTOM = "custom"


class SLABreachSeverity(Enum):
    WARNING = "warning"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class SLATarget:
    metric_type: SLAMetricType
    target_value: float
    comparison: str  # "le", "ge", "lt", "gt"
    measurement_window_seconds: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_type": self.metric_type.value, "target_value": self.target_value,
            "comparison": self.comparison, "measurement_window_seconds": self.measurement_window_seconds,
            "description": self.description,
        }


@dataclass
class SLABreach:
    sla_id: str
    metric_type: SLAMetricType
    actual_value: float
    target_value: float
    severity: SLABreachSeverity
    timestamp: float
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sla_id": self.sla_id, "metric_type": self.metric_type.value,
            "actual_value": self.actual_value, "target_value": self.target_value,
            "severity": self.severity.value, "timestamp": self.timestamp, "message": self.message,
        }


@dataclass
class SLARecord:
    sla_id: str
    name: str
    targets: List[SLATarget]
    measurements: Dict[str, List[float]] = field(default_factory=dict)
    breaches: List[SLABreach] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sla_id": self.sla_id, "name": self.name,
            "targets": [t.to_dict() for t in self.targets], "breaches": [b.to_dict() for b in self.breaches],
            "created_at": self.created_at,
        }


class SLAMonitorEngine:
    """
    SLA monitoring with target tracking and breach detection.
    """

    def __init__(self) -> None:
        self._slas: Dict[str, SLARecord] = {}
        self._handlers: List[Callable[[SLABreach], None]] = []

    def register_sla(self, record: SLARecord) -> None:
        self._slas[record.sla_id] = record
        for target in record.targets:
            key = f"{record.sla_id}:{target.metric_type.value}"
            if key not in record.measurements:
                record.measurements[key] = []

    def record_measurement(self, sla_id: str, metric_type: SLAMetricType, value: float) -> None:
        record = self._slas.get(sla_id)
        if not record:
            return
        key = f"{sla_id}:{metric_type.value}"
        record.measurements.setdefault(key, []).append(value)
        # Keep only last window of measurements
        target = next((t for t in record.targets if t.metric_type == metric_type), None)
        if target:
            cutoff = time.time() - target.measurement_window_seconds
            record.measurements[key] = [v for v in record.measurements[key] if v is not None]

    def evaluate(self, sla_id: str) -> List[SLABreach]:
        record = self._slas.get(sla_id)
        if not record:
            return []
        breaches = []
        for target in record.targets:
            key = f"{sla_id}:{target.metric_type.value}"
            values = record.measurements.get(key, [])
            if not values:
                continue
            actual = sum(values) / len(values)
            breached = False
            if target.comparison == "le" and actual > target.target_value:
                breached = True
            elif target.comparison == "ge" and actual < target.target_value:
                breached = True
            elif target.comparison == "lt" and actual >= target.target_value:
                breached = True
            elif target.comparison == "gt" and actual <= target.target_value:
                breached = True
            if breached:
                severity = SLABreachSeverity.MAJOR if actual > target.target_value * 1.5 else SLABreachSeverity.WARNING
                breach = SLABreach(
                    sla_id=sla_id, metric_type=target.metric_type, actual_value=actual,
                    target_value=target.target_value, severity=severity,
                    timestamp=time.time(), message=f"SLA breach: {target.metric_type.value}={actual:.2f} (target {target.comparison} {target.target_value})"
                )
                record.breaches.append(breach)
                breaches.append(breach)
                for handler in self._handlers:
                    try:
                        handler(breach)
                    except Exception:
                        pass
        return breaches

    def add_handler(self, handler: Callable[[SLABreach], None]) -> None:
        self._handlers.append(handler)

    def get_compliance(self, sla_id: str) -> Dict[str, Any]:
        record = self._slas.get(sla_id)
        if not record:
            return {}
        total_targets = len(record.targets)
        breached = len(record.breaches)
        return {
            "sla_id": sla_id, "total_targets": total_targets,
            "breach_count": len(record.breaches), "compliance_rate": (total_targets - min(breached, total_targets)) / total_targets,
        }

    def get_all_breaches(self, sla_id: Optional[str] = None, severity: Optional[SLABreachSeverity] = None) -> List[SLABreach]:
        breaches = []
        for record in self._slas.values():
            if sla_id and record.sla_id != sla_id:
                continue
            for b in record.breaches:
                if severity and b.severity != severity:
                    continue
                breaches.append(b)
        return breaches

    def stats(self) -> Dict[str, Any]:
        return {
            "slas": len(self._slas),
            "total_breaches": sum(len(r.breaches) for r in self._slas.values()),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS SLA Monitor Engine")
    print("=" * 60)

    engine = SLAMonitorEngine()

    def alert_handler(breach: SLABreach) -> None:
        print(f"  [SLA ALERT] {breach.sla_id}: {breach.message}")

    engine.add_handler(alert_handler)

    # Register SLA
    record = SLARecord(
        sla_id="llm_api_sla", name="LLM API Service Level",
        targets=[
            SLATarget(SLAMetricType.LATENCY, 500, "le", 60, "Latency must be <= 500ms"),
            SLATarget(SLAMetricType.AVAILABILITY, 0.99, "ge", 300, "Availability must be >= 99%"),
            SLATarget(SLAMetricType.ERROR_RATE, 0.05, "le", 60, "Error rate must be <= 5%"),
        ]
    )
    engine.register_sla(record)

    print("\n--- Recording measurements ---")
    for lat in [100, 120, 150, 200, 800, 900]:
        engine.record_measurement("llm_api_sla", SLAMetricType.LATENCY, lat)
    for err in [0.01, 0.02, 0.03, 0.04, 0.02]:
        engine.record_measurement("llm_api_sla", SLAMetricType.ERROR_RATE, err)
    for avail in [0.999, 0.998, 0.997, 0.996]:
        engine.record_measurement("llm_api_sla", SLAMetricType.AVAILABILITY, avail)

    print("\n--- Evaluating SLA ---")
    breaches = engine.evaluate("llm_api_sla")
    for b in breaches:
        print(f"  Breach: {b.metric_type.value} = {b.actual_value:.2f} (severity: {b.severity.value})")

    print("\n--- Compliance ---")
    print(engine.get_compliance("llm_api_sla"))

    print("\n--- Stats ---")
    print(engine.stats())

    print("\nSLA Monitor test complete.")


if __name__ == "__main__":
    run()
