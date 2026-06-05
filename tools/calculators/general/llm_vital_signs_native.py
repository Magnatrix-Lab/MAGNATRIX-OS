"""Vital Signs Monitor — HR, BP, SpO2, temp, alerts, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class VitalSigns:
    heart_rate: float = 70.0
    systolic: float = 120.0
    diastolic: float = 80.0
    spo2: float = 98.0
    temperature: float = 37.0

class VitalSignsMonitor:
    def __init__(self):
        self.history: List[VitalSigns] = []

    def add_reading(self, v: VitalSigns):
        self.history.append(v)

    def alerts(self) -> List[str]:
        if not self.history:
            return []
        v = self.history[-1]
        alerts = []
        if v.heart_rate < 60 or v.heart_rate > 100:
            alerts.append(f"HR abnormal: {v.heart_rate}")
        if v.systolic > 140 or v.diastolic > 90:
            alerts.append(f"Hypertension: {v.systolic}/{v.diastolic}")
        if v.spo2 < 95:
            alerts.append(f"Low SpO2: {v.spo2}")
        if v.temperature > 38.0:
            alerts.append(f"Fever: {v.temperature}")
        return alerts

    def trend(self, field: str) -> str:
        if len(self.history) < 2:
            return "stable"
        vals = [getattr(v, field) for v in self.history]
        if vals[-1] > vals[0] * 1.05:
            return "rising"
        elif vals[-1] < vals[0] * 0.95:
            return "falling"
        return "stable"

    def stats(self) -> Dict:
        if not self.history:
            return {}
        v = self.history[-1]
        return {"hr": v.heart_rate, "bp": f"{v.systolic}/{v.diastolic}", "spo2": v.spo2, "temp": v.temperature, "alerts": len(self.alerts())}

def run():
    vsm = VitalSignsMonitor()
    vsm.add_reading(VitalSigns(75, 120, 80, 98, 36.8))
    vsm.add_reading(VitalSigns(110, 150, 95, 92, 38.5))
    print(vsm.stats())
    print("Alerts:", vsm.alerts())
    print("HR trend:", vsm.trend("heart_rate"))

if __name__ == "__main__":
    run()
