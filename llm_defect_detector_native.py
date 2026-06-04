"""Defect Detector — visual inspection, statistical process control, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import statistics
import math

class DefectDetector:
    def __init__(self, method: str = "spc"):
        self.method = method
        self.measurements: List[float] = []
        self.defects: List[Dict] = []
        self.control_limits = {"ucl": None, "lcl": None, "mean": None}

    def add_measurement(self, value: float):
        self.measurements.append(value)
        if len(self.measurements) >= 5:
            self._update_limits()

    def _update_limits(self):
        mean = statistics.mean(self.measurements)
        std = statistics.stdev(self.measurements) if len(self.measurements) > 1 else 0
        self.control_limits = {"mean": mean, "ucl": mean + 3 * std, "lcl": mean - 3 * std}

    def inspect(self, value: float) -> Dict:
        if self.control_limits["ucl"] is None:
            return {"value": value, "status": "INSPECTING"}
        if value > self.control_limits["ucl"] or value < self.control_limits["lcl"]:
            self.defects.append({"value": value, "time": len(self.measurements), "type": "out_of_control"})
            return {"value": value, "status": "DEFECT", "limit": "exceeded"}
        if abs(value - self.control_limits["mean"]) > 2 * (self.control_limits["ucl"] - self.control_limits["mean"]) / 3:
            return {"value": value, "status": "WARNING"}
        return {"value": value, "status": "OK"}

    def defect_rate(self) -> float:
        return len(self.defects) / len(self.measurements) if self.measurements else 0

    def stats(self) -> Dict:
        return {"measurements": len(self.measurements), "defects": len(self.defects), "defect_rate": self.defect_rate(), "limits": self.control_limits}

def run():
    dd = DefectDetector()
    for v in [10, 11, 10, 12, 11, 10, 15, 10]:
        dd.add_measurement(v)
        print(dd.inspect(v))
    print(dd.stats())

if __name__ == "__main__":
    run()
