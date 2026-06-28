#!/usr/bin/env python3
"""Weather Prediction Engine for MAGNATRIX-OS."""
from __future__ import annotations
import statistics
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

class WeatherPredictionEngine:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.history: List[Dict[str, float]] = []
    def add_reading(self, temp: float, humidity: float, pressure: float):
        self.history.append({"temp": temp, "humidity": humidity, "pressure": pressure})
    def predict(self, days: int = 1) -> Dict[str, Any]:
        if not self.history: return {"error": "no data"}
        temps = [r["temp"] for r in self.history[-30:]]
        if not temps: return {"error": "no data"}
        avg = statistics.mean(temps)
        trend = temps[-1] - temps[0] if len(temps) > 1 else 0
        return {"predicted_temp": round(avg + trend * days, 2), "confidence": 0.6, "days": days}
    def to_dict(self): return {"readings": len(self.history)}
