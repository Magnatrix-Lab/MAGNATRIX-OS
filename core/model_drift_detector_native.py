#!/usr/bin/env python3
"""Model Drift Detector for MAGNATRIX-OS."""
from __future__ import annotations
import statistics
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

class ModelDriftDetector:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.baseline: Dict[str, List[float]] = {}
        self.current: Dict[str, List[float]] = {}
        self.alerts: List[Dict[str, Any]] = []
    def set_baseline(self, metric: str, values: List[float]):
        self.baseline[metric] = values
    def add_current(self, metric: str, value: float):
        if metric not in self.current:
            self.current[metric] = []
        self.current[metric].append(value)
    def detect_drift(self, metric: str, threshold: float = 0.2) -> Dict[str, Any]:
        if metric not in self.baseline or metric not in self.current:
            return {"drift": False, "metric": metric}
        base_mean = statistics.mean(self.baseline[metric])
        curr_mean = statistics.mean(self.current[metric][-50:])
        drift = abs(curr_mean - base_mean) / abs(base_mean) if base_mean != 0 else 0
        is_drift = drift > threshold
        if is_drift:
            self.alerts.append({"metric": metric, "drift": drift, "timestamp": __import__('time').time()})
        return {"drift": is_drift, "metric": metric, "magnitude": round(drift, 4)}
    def detect_all(self) -> List[Dict[str, Any]]:
        return [self.detect_drift(m) for m in self.baseline if m in self.current]
    def to_dict(self): return {"baseline_metrics": len(self.baseline), "alerts": len(self.alerts)}
