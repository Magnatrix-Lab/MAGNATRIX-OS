#!/usr/bin/env python3
"""
Capability Concealment Detection for MAGNATRIX-OS
=================================================
Detects when agents or modules hide their true capabilities.
Behavior analysis, output consistency, hidden capability fingerprinting.
Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import hashlib, json, math, re, statistics, time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ConcealmentType(Enum):
    CAPABILITY_UNDERREPORT = "capability_underreport"
    OUTPUT_INCONSISTENCY = "output_inconsistency"
    BEHAVIORAL_MISMATCH = "behavioral_mismatch"
    DECEPTION_PATTERN = "deception_pattern"
    HIDDEN_CHANNEL = "hidden_channel"


@dataclass
class BehaviorProfile:
    """Baseline behavior profile of a module/agent."""
    module_id: str
    declared_capabilities: List[str] = field(default_factory=list)
    observed_actions: List[str] = field(default_factory=list)
    output_patterns: List[str] = field(default_factory=list)
    latency_ms: List[float] = field(default_factory=list)
    error_rate: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["declared_capabilities"] = self.declared_capabilities
        d["observed_actions"] = self.observed_actions[-100:]
        return d


@dataclass
class ConcealmentAlert:
    """Alert when concealment is detected."""
    module_id: str
    concealment_type: ConcealmentType
    confidence: float
    evidence: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    severity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["concealment_type"] = self.concealment_type.value
        return d


class BehaviorAnalyzer:
    """Analyzes module behavior for anomalies."""

    def __init__(self, window_size: int = 1000) -> None:
        self.profiles: Dict[str, BehaviorProfile] = {}
        self._lock = object()
        self.window_size = window_size

    def register(self, module_id: str, declared_capabilities: List[str]) -> None:
        self.profiles[module_id] = BehaviorProfile(
            module_id=module_id,
            declared_capabilities=declared_capabilities,
        )

    def record_action(self, module_id: str, action: str, latency_ms: float = 0.0, error: bool = False) -> None:
        profile = self.profiles.get(module_id)
        if not profile:
            return
        profile.observed_actions.append(action)
        profile.latency_ms.append(latency_ms)
        if error:
            profile.error_rate = min(1.0, profile.error_rate + 0.01)
        else:
            profile.error_rate = max(0.0, profile.error_rate * 0.99)
        if len(profile.observed_actions) > self.window_size:
            profile.observed_actions = profile.observed_actions[-self.window_size:]
        if len(profile.latency_ms) > self.window_size:
            profile.latency_ms = profile.latency_ms[-self.window_size:]
        profile.updated_at = time.time()

    def record_output(self, module_id: str, output: str) -> None:
        profile = self.profiles.get(module_id)
        if not profile:
            return
        pattern = self._extract_pattern(output)
        if pattern not in profile.output_patterns:
            profile.output_patterns.append(pattern)
        profile.updated_at = time.time()

    def _extract_pattern(self, output: str) -> str:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', output.lower())
        if not words:
            return ""
        return " ".join(sorted(set(words))[:10])

    def detect_capability_gap(self, module_id: str) -> Tuple[float, List[str]]:
        """Detect declared vs observed capability gaps."""
        profile = self.profiles.get(module_id)
        if not profile or not profile.declared_capabilities:
            return 0.0, []
        observed_set = set()
        for action in profile.observed_actions:
            for cap in profile.declared_capabilities:
                if cap.lower() in action.lower():
                    observed_set.add(cap)
        gap = [c for c in profile.declared_capabilities if c not in observed_set]
        if not gap:
            return 0.0, []
        confidence = len(gap) / len(profile.declared_capabilities)
        return min(confidence, 1.0), gap

    def detect_inconsistency(self, module_id: str) -> Tuple[float, List[str]]:
        """Detect output pattern inconsistencies."""
        profile = self.profiles.get(module_id)
        if not profile or len(profile.output_patterns) < 2:
            return 0.0, []
        evidence = []
        for i, p1 in enumerate(profile.output_patterns[-5:]):
            for p2 in profile.output_patterns[-5:][i+1:]:
                if p1 and p2 and abs(len(p1) - len(p2)) > 50:
                    evidence.append(f"Output size variance: {len(p1)} vs {len(p2)}")
        if not evidence:
            return 0.0, []
        return min(len(evidence) / 5.0, 1.0), evidence

    def detect_latency_anomaly(self, module_id: str) -> Tuple[float, List[str]]:
        """Detect latency anomalies suggesting hidden processing."""
        profile = self.profiles.get(module_id)
        if not profile or len(profile.latency_ms) < 10:
            return 0.0, []
        recent = profile.latency_ms[-50:]
        if not recent:
            return 0.0, []
        mean_lat = statistics.mean(recent)
        std_lat = statistics.stdev(recent) if len(recent) > 1 else 0.0
        if std_lat == 0:
            return 0.0, []
        outliers = [l for l in recent if abs(l - mean_lat) > 3 * std_lat]
        if not outliers:
            return 0.0, []
        evidence = [f"Latency spike: {o:.1f}ms (mean: {mean_lat:.1f}ms, std: {std_lat:.1f}ms)" for o in outliers[:3]]
        confidence = min(len(outliers) / len(recent), 1.0)
        return confidence, evidence

    def get_profile(self, module_id: str) -> Optional[BehaviorProfile]:
        return self.profiles.get(module_id)

    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        return {k: v.to_dict() for k, v in self.profiles.items()}


class ConcealmentDetector:
    """Main detector for capability concealment."""

    def __init__(self, confidence_threshold: float = 0.7) -> None:
        self.analyzer = BehaviorAnalyzer()
        self.confidence_threshold = confidence_threshold
        self.alerts: List[ConcealmentAlert] = []
        self._fingerprint_db: Dict[str, str] = {}

    def register_module(self, module_id: str, declared_capabilities: List[str]) -> None:
        self.analyzer.register(module_id, declared_capabilities)

    def record(self, module_id: str, action: str, output: str = "", latency_ms: float = 0.0, error: bool = False) -> None:
        self.analyzer.record_action(module_id, action, latency_ms, error)
        self.analyzer.record_output(module_id, output)

    def scan(self, module_id: str) -> List[ConcealmentAlert]:
        """Scan a module for concealment indicators."""
        alerts = []
        # Check capability gap
        conf, gap = self.analyzer.detect_capability_gap(module_id)
        if conf >= self.confidence_threshold and gap:
            alerts.append(ConcealmentAlert(
                module_id=module_id,
                concealment_type=ConcealmentType.CAPABILITY_UNDERREPORT,
                confidence=conf,
                evidence=[f"Never observed: {c}" for c in gap[:5]],
                severity="high" if conf > 0.9 else "medium",
            ))
        # Check inconsistency
        conf, evidence = self.analyzer.detect_inconsistency(module_id)
        if conf >= self.confidence_threshold and evidence:
            alerts.append(ConcealmentAlert(
                module_id=module_id,
                concealment_type=ConcealmentType.OUTPUT_INCONSISTENCY,
                confidence=conf,
                evidence=evidence,
                severity="medium",
            ))
        # Check latency anomaly
        conf, evidence = self.analyzer.detect_latency_anomaly(module_id)
        if conf >= self.confidence_threshold and evidence:
            alerts.append(ConcealmentAlert(
                module_id=module_id,
                concealment_type=ConcealmentType.BEHAVIORAL_MISMATCH,
                confidence=conf,
                evidence=evidence,
                severity="low" if conf < 0.8 else "medium",
            ))
        # Detect deception patterns in output
        profile = self.analyzer.get_profile(module_id)
        if profile and profile.output_patterns:
            deception_evidence = self._check_deception_patterns(profile.output_patterns[-1])
            if deception_evidence:
                alerts.append(ConcealmentAlert(
                    module_id=module_id,
                    concealment_type=ConcealmentType.DECEPTION_PATTERN,
                    confidence=0.75,
                    evidence=deception_evidence,
                    severity="high",
                ))
        self.alerts.extend(alerts)
        return alerts

    def _check_deception_patterns(self, output_pattern: str) -> List[str]:
        evidence = []
        deception_markers = [
            "i cannot", "i am unable", "not allowed", "restricted",
            "policy prevents", "compliance", "terms of service",
            "i'm just", "i can only", "my purpose is",
        ]
        pattern_lower = output_pattern.lower()
        for marker in deception_markers:
            if marker in pattern_lower:
                evidence.append(f"Deception marker: '{marker}'")
        return evidence

    def scan_all(self) -> Dict[str, List[ConcealmentAlert]]:
        results = {}
        for module_id in self.analyzer.profiles:
            alerts = self.scan(module_id)
            if alerts:
                results[module_id] = alerts
        return results

    def get_alerts(self, module_id: Optional[str] = None) -> List[ConcealmentAlert]:
        if module_id:
            return [a for a in self.alerts if a.module_id == module_id]
        return self.alerts.copy()

    def get_risk_score(self, module_id: str) -> float:
        module_alerts = self.get_alerts(module_id)
        if not module_alerts:
            return 0.0
        max_conf = max(a.confidence for a in module_alerts)
        severity_weights = {"low": 0.3, "medium": 0.6, "high": 1.0}
        weighted = sum(a.confidence * severity_weights.get(a.severity, 0.5) for a in module_alerts)
        return min(weighted / len(module_alerts) + max_conf * 0.3, 1.0)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_modules": len(self.analyzer.profiles),
            "total_alerts": len(self.alerts),
            "modules_at_risk": len(set(a.module_id for a in self.alerts)),
            "high_severity": sum(1 for a in self.alerts if a.severity == "high"),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.get_summary(),
            "alerts": [a.to_dict() for a in self.alerts[-50:]],
        }
