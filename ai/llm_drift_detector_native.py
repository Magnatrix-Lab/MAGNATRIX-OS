#!/usr/bin/env python3
"""
MAGNATRIX-OS — Drift Detection Engine
ai/llm_drift_detector_native.py

Features:
- Concept drift detection (KS-test, chi-square simulation)
- Data drift monitoring (feature distribution changes)
- Performance drift tracking (accuracy, latency, error rate trends)
- Drift alert system with severity levels
- Baseline profile management and window comparison

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("drift_detector")


class DriftSeverity(enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DriftType(enum.Enum):
    CONCEPT = "concept"       # output distribution drift
    DATA = "data"             # input feature distribution drift
    PERFORMANCE = "performance"  # accuracy/latency/error rate drift


@dataclass
class DistributionProfile:
    """Statistical profile of a data distribution."""
    mean: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    median: float = 0.0
    samples: int = 0
    histogram: Dict[str, int] = field(default_factory=dict)
    timestamp: float = 0.0

    @classmethod
    def from_values(cls, values: List[float]) -> "DistributionProfile":
        if not values:
            return cls()
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mean = sum(sorted_vals) / n
        variance = sum((x - mean) ** 2 for x in sorted_vals) / n
        std = math.sqrt(variance) if variance > 0 else 0.0
        median = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        # Simple histogram bins
        bins = {}
        for v in sorted_vals:
            b = round(v, 1)
            bins[str(b)] = bins.get(str(b), 0) + 1
        return cls(
            mean=mean, std=std, min_val=min(sorted_vals), max_val=max(sorted_vals),
            median=median, samples=n, histogram=bins, timestamp=time.monotonic(),
        )


@dataclass
class DriftReport:
    drift_type: DriftType
    severity: DriftSeverity
    score: float
    threshold: float
    metric_name: str
    baseline_window: str
    current_window: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    @property
    def is_drift(self) -> bool:
        return self.severity != DriftSeverity.NONE


class StatisticalTests:
    """Simulated statistical tests for drift detection."""

    @staticmethod
    def ks_distance(baseline: DistributionProfile, current: DistributionProfile) -> float:
        """Kolmogorov-Smirnov distance approximation."""
        if baseline.std == 0 or current.std == 0:
            return 0.0 if baseline.mean == current.mean else 1.0
        # Use mean difference normalized by combined std
        combined_std = max((baseline.std + current.std) / 2, 1e-6)
        return min(abs(baseline.mean - current.mean) / combined_std, 1.0)

    @staticmethod
    def chi_square_sim(baseline: DistributionProfile, current: DistributionProfile) -> float:
        """Simulated chi-square test on histograms."""
        all_keys = set(baseline.histogram.keys()) | set(current.histogram.keys())
        total_baseline = sum(baseline.histogram.values()) or 1
        total_current = sum(current.histogram.values()) or 1
        chi2 = 0.0
        for key in all_keys:
            expected = (baseline.histogram.get(key, 0) / total_baseline) * total_current
            observed = current.histogram.get(key, 0)
            if expected > 0:
                chi2 += (observed - expected) ** 2 / expected
        return chi2

    @staticmethod
    def z_score_drift(baseline: DistributionProfile, current: DistributionProfile) -> float:
        """Z-score based drift detection."""
        if baseline.std == 0:
            return 0.0 if current.mean == baseline.mean else 1.0
        z = abs(current.mean - baseline.mean) / baseline.std
        return min(z / 3.0, 1.0)  # normalize to 0-1


class DriftDetector:
    """Drift detection engine with windowed monitoring."""

    def __init__(self, window_size: int = 100, alert_threshold: float = 0.7):
        self._window_size = window_size
        self._alert_threshold = alert_threshold
        self._baseline: Dict[str, DistributionProfile] = {}
        self._windows: Dict[str, Deque[float]] = {}
        self._reports: List[DriftReport] = []
        self._tests = StatisticalTests()

    def set_baseline(self, metric_name: str, values: List[float]) -> None:
        self._baseline[metric_name] = DistributionProfile.from_values(values)
        logger.info(f"Baseline set for {metric_name}: n={len(values)}, mean={self._baseline[metric_name].mean:.3f}")

    def observe(self, metric_name: str, value: float) -> Optional[DriftReport]:
        if metric_name not in self._windows:
            self._windows[metric_name] = deque(maxlen=self._window_size)
        self._windows[metric_name].append(value)
        if len(self._windows[metric_name]) >= self._window_size // 2:
            return self._check_drift(metric_name)
        return None

    def _check_drift(self, metric_name: str) -> Optional[DriftReport]:
        baseline = self._baseline.get(metric_name)
        if not baseline:
            return None
        current_vals = list(self._windows[metric_name])
        current = DistributionProfile.from_values(current_vals)
        ks = self._tests.ks_distance(baseline, current)
        chi2 = self._tests.chi_square_sim(baseline, current)
        z = self._tests.z_score_drift(baseline, current)
        # Combined drift score
        score = max(ks, z)
        severity = self._severity(score)
        report = DriftReport(
            drift_type=DriftType.DATA,
            severity=severity,
            score=score,
            threshold=self._alert_threshold,
            metric_name=metric_name,
            baseline_window=f"n={baseline.samples}, mean={baseline.mean:.3f}",
            current_window=f"n={current.samples}, mean={current.mean:.3f}",
            details={"ks_distance": ks, "chi2": chi2, "z_score": z},
            timestamp=time.monotonic(),
        )
        self._reports.append(report)
        if severity in (DriftSeverity.MEDIUM, DriftSeverity.HIGH, DriftSeverity.CRITICAL):
            logger.warning(f"Drift detected on {metric_name}: {severity.value} (score={score:.3f})")
        return report

    def _severity(self, score: float) -> DriftSeverity:
        if score < 0.2:
            return DriftSeverity.NONE
        elif score < 0.4:
            return DriftSeverity.LOW
        elif score < 0.6:
            return DriftSeverity.MEDIUM
        elif score < 0.8:
            return DriftSeverity.HIGH
        return DriftSeverity.CRITICAL

    def get_reports(self, metric_name: Optional[str] = None) -> List[DriftReport]:
        if metric_name:
            return [r for r in self._reports if r.metric_name == metric_name]
        return list(self._reports)

    def reset(self, metric_name: Optional[str] = None) -> None:
        if metric_name:
            self._windows.pop(metric_name, None)
            self._baseline.pop(metric_name, None)
            self._reports = [r for r in self._reports if r.metric_name != metric_name]
        else:
            self._windows.clear()
            self._baseline.clear()
            self._reports.clear()


class PerformanceMonitor:
    """Monitor performance metrics for drift."""

    def __init__(self, detector: DriftDetector):
        self._detector = detector
        self._accuracy_history: Deque[float] = deque(maxlen=500)
        self._latency_history: Deque[float] = deque(maxlen=500)
        self._error_history: Deque[float] = deque(maxlen=500)

    def record(self, accuracy: float, latency_ms: float, error: bool) -> Optional[DriftReport]:
        self._accuracy_history.append(accuracy)
        self._latency_history.append(latency_ms)
        self._error_history.append(1.0 if error else 0.0)
        reports = []
        if len(self._accuracy_history) >= 50:
            report = self._detector.observe("accuracy", accuracy)
            if report:
                reports.append(report)
            report = self._detector.observe("latency_ms", latency_ms)
            if report:
                reports.append(report)
            report = self._detector.observe("error_rate", 1.0 if error else 0.0)
            if report:
                reports.append(report)
        return reports[0] if reports else None

    def set_baselines(self, accuracies: List[float], latencies: List[float], errors: List[float]) -> None:
        self._detector.set_baseline("accuracy", accuracies)
        self._detector.set_baseline("latency_ms", latencies)
        self._detector.set_baseline("error_rate", errors)


class AlertManager:
    """Drift alert system."""

    def __init__(self):
        self._alerts: List[DriftReport] = []
        self._suppress_severity: DriftSeverity = DriftSeverity.LOW

    def set_suppression(self, min_severity: DriftSeverity) -> None:
        self._suppress_severity = min_severity

    def on_drift(self, report: DriftReport) -> None:
        if report.severity in (DriftSeverity.MEDIUM, DriftSeverity.HIGH, DriftSeverity.CRITICAL):
            self._alerts.append(report)
            logger.warning(f"ALERT: {report.metric_name} drift={report.severity.value} score={report.score:.3f}")

    def get_alerts(self) -> List[DriftReport]:
        return list(self._alerts)

    def clear(self) -> None:
        self._alerts.clear()


class DriftDetectionEngine:
    """Unified drift detection engine."""

    def __init__(self, window_size: int = 100, alert_threshold: float = 0.7):
        self.detector = DriftDetector(window_size, alert_threshold)
        self.performance = PerformanceMonitor(self.detector)
        self.alerts = AlertManager()

    def set_baseline(self, metric_name: str, values: List[float]) -> None:
        self.detector.set_baseline(metric_name, values)

    def observe(self, metric_name: str, value: float) -> Optional[DriftReport]:
        report = self.detector.observe(metric_name, value)
        if report and report.is_drift:
            self.alerts.on_drift(report)
        return report

    def record_performance(self, accuracy: float, latency_ms: float, error: bool) -> Optional[DriftReport]:
        reports = self.performance.record(accuracy, latency_ms, error)
        if reports:
            if isinstance(reports, DriftReport):
                reports = [reports]
            for r in reports:
                if r and r.is_drift:
                    self.alerts.on_drift(r)
            return reports[0] if reports else None
        return None

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_reports": len(self.detector.get_reports()),
            "total_alerts": len(self.alerts.get_alerts()),
            "active_baselines": list(self.detector._baseline.keys()),
            "active_windows": {k: len(v) for k, v in self.detector._windows.items()},
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Drift Detection Engine")
    print("ai/llm_drift_detector_native.py")
    print("=" * 60)

    engine = DriftDetectionEngine(window_size=50, alert_threshold=0.6)

    # 1. Set baseline
    print("")
    print("[1] Baseline Setup")
    baseline = [random.gauss(0.85, 0.05) for _ in range(100)]
    engine.set_baseline("accuracy", baseline)
    print(f"  Baseline accuracy: mean={sum(baseline)/len(baseline):.3f}, std={math.sqrt(sum((x-sum(baseline)/len(baseline))**2 for x in baseline)/len(baseline)):.3f}")

    # 2. Normal observations (no drift)
    print("")
    print("[2] Normal Observations (no drift)")
    for i in range(30):
        val = random.gauss(0.85, 0.05)
        report = engine.observe("accuracy", val)
    print(f"  Observed 30 values. Reports: {len(engine.detector.get_reports('accuracy'))}")

    # 3. Induce drift (lower accuracy)
    print("")
    print("[3] Inducing Drift (accuracy drops to 0.6)")
    for i in range(40):
        val = random.gauss(0.60, 0.08)
        report = engine.observe("accuracy", val)
        if report and report.is_drift:
            print(f"  Drift detected! severity={report.severity.value}, score={report.score:.3f}, ks={report.details['ks_distance']:.3f}")
            break

    # 4. Performance monitoring
    print("")
    print("[4] Performance Monitoring")
    engine.performance.set_baselines(
        accuracies=[random.gauss(0.85, 0.05) for _ in range(100)],
        latencies=[random.gauss(120, 20) for _ in range(100)],
        errors=[0.0] * 95 + [1.0] * 5,
    )
    for i in range(50):
        acc = random.gauss(0.70, 0.10)
        lat = random.gauss(200, 30)
        err = random.random() < 0.15
        report = engine.record_performance(acc, lat, err)
    alerts = engine.alerts.get_alerts()
    print(f"  Recorded 50 performance samples. Alerts: {len(alerts)}")
    for alert in alerts[:3]:
        print(f"    [{alert.severity.value}] {alert.metric_name}: score={alert.score:.3f}")

    # 5. Summary
    print("")
    print("[5] Engine Summary")
    summary = engine.get_summary()
    print(f"  {summary}")

    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
